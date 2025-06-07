"""Test for the SmartThings fan platform."""

from unittest.mock import AsyncMock

from pysmartthings import Capability, Command
from pysmartthings.models import HealthStatus
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.fan import (
    ATTR_PERCENTAGE,
    ATTR_PRESET_MODE,
    DOMAIN as FAN_DOMAIN,
    SERVICE_SET_PERCENTAGE,
    SERVICE_SET_PRESET_MODE,
)
from menuai.components.smartthings import MAIN
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_UNAVAILABLE,
    Platform,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration, snapshot_smartthings_entities, trigger_health_update

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

    snapshot_smartthings_entities(menuai, entity_registry, snapshot, Platform.FAN)


@pytest.mark.parametrize("device_fixture", ["fake_fan"])
@pytest.mark.parametrize(
    ("action", "command"),
    [
        (SERVICE_TURN_ON, Command.ON),
        (SERVICE_TURN_OFF, Command.OFF),
    ],
)
async def test_turn_on_off(
    menuai: menuai,
    devices: AsyncMock,
    mock_config_entry: MockConfigEntry,
    action: str,
    command: Command,
) -> None:
    """Test turning on and off."""
    await setup_integration(menuai, mock_config_entry)

    await menuai.services.async_call(
        FAN_DOMAIN,
        action,
        {ATTR_ENTITY_ID: "fan.fake_fan"},
        blocking=True,
    )
    devices.execute_device_command.assert_called_once_with(
        "f1af21a2-d5a1-437c-b10a-b34a87394b71",
        Capability.SWITCH,
        command,
        MAIN,
    )


@pytest.mark.parametrize("device_fixture", ["fake_fan"])
async def test_set_percentage(
    menuai: menuai,
    devices: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setting the speed percentage of the fan."""
    await setup_integration(menuai, mock_config_entry)

    await menuai.services.async_call(
        FAN_DOMAIN,
        SERVICE_SET_PERCENTAGE,
        {ATTR_ENTITY_ID: "fan.fake_fan", ATTR_PERCENTAGE: 50},
        blocking=True,
    )
    devices.execute_device_command.assert_called_once_with(
        "f1af21a2-d5a1-437c-b10a-b34a87394b71",
        Capability.FAN_SPEED,
        Command.SET_FAN_SPEED,
        MAIN,
        argument=2,
    )


@pytest.mark.parametrize("device_fixture", ["fake_fan"])
async def test_set_percentage_off(
    menuai: menuai,
    devices: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setting the speed percentage of the fan."""
    await setup_integration(menuai, mock_config_entry)

    await menuai.services.async_call(
        FAN_DOMAIN,
        SERVICE_SET_PERCENTAGE,
        {ATTR_ENTITY_ID: "fan.fake_fan", ATTR_PERCENTAGE: 0},
        blocking=True,
    )
    devices.execute_device_command.assert_called_once_with(
        "f1af21a2-d5a1-437c-b10a-b34a87394b71",
        Capability.SWITCH,
        Command.OFF,
        MAIN,
    )


@pytest.mark.parametrize("device_fixture", ["fake_fan"])
async def test_set_percentage_on(
    menuai: menuai,
    devices: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setting the speed percentage of the fan."""
    await setup_integration(menuai, mock_config_entry)

    await menuai.services.async_call(
        FAN_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "fan.fake_fan", ATTR_PERCENTAGE: 50},
        blocking=True,
    )
    devices.execute_device_command.assert_called_once_with(
        "f1af21a2-d5a1-437c-b10a-b34a87394b71",
        Capability.FAN_SPEED,
        Command.SET_FAN_SPEED,
        MAIN,
        argument=2,
    )


@pytest.mark.parametrize("device_fixture", ["fake_fan"])
async def test_set_preset_mode(
    menuai: menuai,
    devices: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setting the speed percentage of the fan."""
    await setup_integration(menuai, mock_config_entry)

    await menuai.services.async_call(
        FAN_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: "fan.fake_fan", ATTR_PRESET_MODE: "turbo"},
        blocking=True,
    )
    devices.execute_device_command.assert_called_once_with(
        "f1af21a2-d5a1-437c-b10a-b34a87394b71",
        Capability.AIR_CONDITIONER_FAN_MODE,
        Command.SET_FAN_MODE,
        MAIN,
        argument="turbo",
    )


@pytest.mark.parametrize("device_fixture", ["fake_fan"])
async def test_availability(
    menuai: menuai,
    devices: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test availability."""
    await setup_integration(menuai, mock_config_entry)

    assert menuai.states.get("fan.fake_fan").state == STATE_OFF

    await trigger_health_update(
        menuai, devices, "f1af21a2-d5a1-437c-b10a-b34a87394b71", HealthStatus.OFFLINE
    )

    assert menuai.states.get("fan.fake_fan").state == STATE_UNAVAILABLE

    await trigger_health_update(
        menuai, devices, "f1af21a2-d5a1-437c-b10a-b34a87394b71", HealthStatus.ONLINE
    )

    assert menuai.states.get("fan.fake_fan").state == STATE_OFF


@pytest.mark.parametrize("device_fixture", ["fake_fan"])
async def test_availability_at_start(
    menuai: menuai,
    unavailable_device: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test unavailable at boot."""
    await setup_integration(menuai, mock_config_entry)
    assert menuai.states.get("fan.fake_fan").state == STATE_UNAVAILABLE
