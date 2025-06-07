"""Test Renault diagnostics."""

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.renault import DOMAIN
from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from tests.components.diagnostics import (
    get_diagnostics_for_config_entry,
    get_diagnostics_for_device,
)
from tests.typing import ClientSessionGenerator

pytestmark = pytest.mark.usefixtures("patch_renault_account", "patch_get_vehicles")


@pytest.mark.usefixtures("fixtures_with_data")
@pytest.mark.parametrize("vehicle_type", ["zoe_40"], indirect=True)
async def test_entry_diagnostics(
    menuai: menuai,
    config_entry: ConfigEntry,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test config entry diagnostics."""
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert (
        await get_diagnostics_for_config_entry(menuai, menuai_client, config_entry)
        == snapshot
    )


@pytest.mark.usefixtures("fixtures_with_data")
@pytest.mark.parametrize("vehicle_type", ["zoe_40"], indirect=True)
async def test_device_diagnostics(
    menuai: menuai,
    config_entry: ConfigEntry,
    device_registry: dr.DeviceRegistry,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test config entry diagnostics."""
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    device = device_registry.async_get_device(identifiers={(DOMAIN, "VF1ZOE40VIN")})
    assert device is not None

    assert (
        await get_diagnostics_for_device(menuai, menuai_client, config_entry, device)
        == snapshot
    )
