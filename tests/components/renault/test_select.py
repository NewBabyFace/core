"""Tests for Renault selects."""

from collections.abc import Generator
from unittest.mock import patch

import pytest
from renault_api.kamereon import schemas
from syrupy.assertion import SnapshotAssertion

from menuai.components.renault.const import DOMAIN
from menuai.components.select import (
    ATTR_OPTION,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from menuai.config_entries import ConfigEntry
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .const import MOCK_VEHICLES

from tests.common import async_load_fixture, snapshot_platform

pytestmark = pytest.mark.usefixtures("patch_renault_account", "patch_get_vehicles")


# Captur (fuel version) does not have a charge mode select
_TEST_VEHICLES = [v for v in MOCK_VEHICLES if v != "captur_fuel"]


@pytest.fixture(autouse=True)
def override_platforms() -> Generator[None]:
    """Override PLATFORMS."""
    with patch("menuai.components.renault.PLATFORMS", [Platform.SELECT]):
        yield


@pytest.mark.usefixtures("fixtures_with_data")
@pytest.mark.parametrize("vehicle_type", _TEST_VEHICLES, indirect=True)
async def test_selects(
    menuai: menuai,
    config_entry: ConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test for Renault selects."""
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    await snapshot_platform(menuai, entity_registry, snapshot, config_entry.entry_id)


@pytest.mark.usefixtures("fixtures_with_no_data")
@pytest.mark.parametrize("vehicle_type", ["zoe_40"], indirect=True)
async def test_select_empty(
    menuai: menuai,
    config_entry: ConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test for Renault selects with empty data from Renault."""
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    await snapshot_platform(menuai, entity_registry, snapshot, config_entry.entry_id)


@pytest.mark.usefixtures("fixtures_with_invalid_upstream_exception")
@pytest.mark.parametrize("vehicle_type", ["zoe_40"], indirect=True)
async def test_select_errors(
    menuai: menuai,
    config_entry: ConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test for Renault selects with temporary failure."""
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    await snapshot_platform(menuai, entity_registry, snapshot, config_entry.entry_id)


@pytest.mark.usefixtures("fixtures_with_access_denied_exception")
@pytest.mark.parametrize("vehicle_type", ["zoe_40"], indirect=True)
async def test_select_access_denied(
    menuai: menuai,
    config_entry: ConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test for Renault selects with access denied failure."""
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert len(entity_registry.entities) == 0


@pytest.mark.usefixtures("fixtures_with_not_supported_exception")
@pytest.mark.parametrize("vehicle_type", ["zoe_40"], indirect=True)
async def test_select_not_supported(
    menuai: menuai,
    config_entry: ConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test for Renault selects with access denied failure."""
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert len(entity_registry.entities) == 0


@pytest.mark.usefixtures("fixtures_with_data")
@pytest.mark.parametrize("vehicle_type", ["zoe_40"], indirect=True)
async def test_select_charge_mode(
    menuai: menuai, config_entry: ConfigEntry
) -> None:
    """Test that service invokes renault_api with correct data."""
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    data = {
        ATTR_ENTITY_ID: "select.reg_zoe_40_charge_mode",
        ATTR_OPTION: "always",
    }

    with patch(
        "renault_api.renault_vehicle.RenaultVehicle.set_charge_mode",
        return_value=(
            schemas.KamereonVehicleHvacStartActionDataSchema.loads(
                await async_load_fixture(menuai, "action.set_charge_mode.json", DOMAIN)
            )
        ),
    ) as mock_action:
        await menuai.services.async_call(
            SELECT_DOMAIN, SERVICE_SELECT_OPTION, service_data=data, blocking=True
        )
    assert len(mock_action.mock_calls) == 1
    assert mock_action.mock_calls[0][1] == ("always",)
