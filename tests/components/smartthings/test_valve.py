"""Test for the SmartThings valve platform."""

from unittest.mock import AsyncMock

from pysmartthings import Attribute, Capability, Command
from pysmartthings.models import HealthStatus
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.smartthings import MAIN
from menuai.components.valve import DOMAIN as VALVE_DOMAIN, ValveState
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_CLOSE_VALVE,
    SERVICE_OPEN_VALVE,
    STATE_UNAVAILABLE,
    Platform,
)
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

    snapshot_smartthings_entities(menuai, entity_registry, snapshot, Platform.VALVE)


@pytest.mark.parametrize("device_fixture", ["virtual_valve"])
@pytest.mark.parametrize(
    ("action", "command"),
    [
        (SERVICE_OPEN_VALVE, Command.OPEN),
        (SERVICE_CLOSE_VALVE, Command.CLOSE),
    ],
)
async def test_valve_open_close(
    menuai: menuai,
    devices: AsyncMock,
    mock_config_entry: MockConfigEntry,
    action: str,
    command: Command,
) -> None:
    """Test valve open and close command."""
    await setup_integration(menuai, mock_config_entry)

    await menuai.services.async_call(
        VALVE_DOMAIN,
        action,
        {ATTR_ENTITY_ID: "valve.volvo"},
        blocking=True,
    )
    devices.execute_device_command.assert_called_once_with(
        "612ab3c2-3bb0-48f7-b2c0-15b169cb2fc3", Capability.VALVE, command, MAIN
    )


@pytest.mark.parametrize("device_fixture", ["virtual_valve"])
async def test_state_update(
    menuai: menuai,
    devices: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test state update."""
    await setup_integration(menuai, mock_config_entry)

    assert menuai.states.get("valve.volvo").state == ValveState.CLOSED

    await trigger_update(
        menuai,
        devices,
        "612ab3c2-3bb0-48f7-b2c0-15b169cb2fc3",
        Capability.VALVE,
        Attribute.VALVE,
        "open",
    )

    assert menuai.states.get("valve.volvo").state == ValveState.OPEN


@pytest.mark.parametrize("device_fixture", ["virtual_valve"])
async def test_availability(
    menuai: menuai,
    devices: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test availability."""
    await setup_integration(menuai, mock_config_entry)

    assert menuai.states.get("valve.volvo").state == ValveState.CLOSED

    await trigger_health_update(
        menuai, devices, "612ab3c2-3bb0-48f7-b2c0-15b169cb2fc3", HealthStatus.OFFLINE
    )

    assert menuai.states.get("valve.volvo").state == STATE_UNAVAILABLE

    await trigger_health_update(
        menuai, devices, "612ab3c2-3bb0-48f7-b2c0-15b169cb2fc3", HealthStatus.ONLINE
    )

    assert menuai.states.get("valve.volvo").state == ValveState.CLOSED


@pytest.mark.parametrize("device_fixture", ["virtual_valve"])
async def test_availability_at_start(
    menuai: menuai,
    unavailable_device: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test unavailable at boot."""
    await setup_integration(menuai, mock_config_entry)
    assert menuai.states.get("valve.volvo").state == STATE_UNAVAILABLE
