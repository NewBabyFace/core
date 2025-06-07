"""Test for the SmartThings number platform."""

from unittest.mock import AsyncMock

from pysmartthings import Attribute, Capability, Command
from pysmartthings.models import HealthStatus
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from menuai.components.smartthings import MAIN
from menuai.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import (
    setup_integration,
    snapshot_smartthings_entities,
    trigger_health_update,
    trigger_update,
)

from tests.common import MockConfigEntry


async def test_all_entities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    devices: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    await setup_integration(menuai, mock_config_entry)

    snapshot_smartthings_entities(menuai, entity_registry, snapshot, Platform.NUMBER)


@pytest.mark.parametrize("device_fixture", ["da_wm_wm_000001"])
async def test_set_value(
    menuai: menuai,
    devices: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setting a value."""
    await setup_integration(menuai, mock_config_entry)

    await menuai.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: "number.washer_rinse_cycles", ATTR_VALUE: 3},
        blocking=True,
    )
    devices.execute_device_command.assert_called_once_with(
        "f984b91d-f250-9d42-3436-33f09a422a47",
        Capability.CUSTOM_WASHER_RINSE_CYCLES,
        Command.SET_WASHER_RINSE_CYCLES,
        MAIN,
        argument="3",
    )


@pytest.mark.parametrize("device_fixture", ["da_wm_wm_000001"])
async def test_state_update(
    menuai: menuai,
    devices: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test state update."""
    await setup_integration(menuai, mock_config_entry)

    assert menuai.states.get("number.washer_rinse_cycles").state == "2"

    await trigger_update(
        menuai,
        devices,
        "f984b91d-f250-9d42-3436-33f09a422a47",
        Capability.CUSTOM_WASHER_RINSE_CYCLES,
        Attribute.WASHER_RINSE_CYCLES,
        "3",
    )

    assert menuai.states.get("number.washer_rinse_cycles").state == "3"


@pytest.mark.parametrize("device_fixture", ["da_wm_wm_000001"])
async def test_availability(
    menuai: menuai,
    devices: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test availability."""
    await setup_integration(menuai, mock_config_entry)

    assert menuai.states.get("number.washer_rinse_cycles").state == "2"

    await trigger_health_update(
        menuai, devices, "f984b91d-f250-9d42-3436-33f09a422a47", HealthStatus.OFFLINE
    )

    assert menuai.states.get("number.washer_rinse_cycles").state == STATE_UNAVAILABLE

    await trigger_health_update(
        menuai, devices, "f984b91d-f250-9d42-3436-33f09a422a47", HealthStatus.ONLINE
    )

    assert menuai.states.get("number.washer_rinse_cycles").state == "2"


@pytest.mark.parametrize("device_fixture", ["da_wm_wm_000001"])
async def test_availability_at_start(
    menuai: menuai,
    unavailable_device: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test unavailable at boot."""
    await setup_integration(menuai, mock_config_entry)
    assert menuai.states.get("number.washer_rinse_cycles").state == STATE_UNAVAILABLE
