"""Test Snooz fan entity."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import Mock, patch

from pysnooz.api import SnoozDeviceState, UnknownSnoozState
from pysnooz.commands import SnoozCommandResult, SnoozCommandResultStatus
from pysnooz.testing import MockSnoozDevice
import pytest

from menuai.components import fan
from menuai.components.snooz.const import (
    ATTR_DURATION,
    DOMAIN,
    SERVICE_TRANSITION_OFF,
    SERVICE_TRANSITION_ON,
)
from menuai.const import (
    ATTR_ASSUMED_STATE,
    ATTR_ENTITY_ID,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    Platform,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er

from . import SnoozFixture, create_mock_snooz, create_mock_snooz_config_entry

from tests.components.bluetooth import generate_ble_device


async def test_turn_on(menuai: menuai, snooz_fan_entity_id: str) -> None:
    """Test turning on the device."""
    await menuai.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: [snooz_fan_entity_id]},
        blocking=True,
    )

    state = menuai.states.get(snooz_fan_entity_id)
    assert state.state == STATE_ON
    assert ATTR_ASSUMED_STATE not in state.attributes


async def test_transition_on(menuai: menuai, snooz_fan_entity_id: str) -> None:
    """Test transitioning on the device."""
    await menuai.services.async_call(
        DOMAIN,
        SERVICE_TRANSITION_ON,
        {ATTR_ENTITY_ID: [snooz_fan_entity_id], ATTR_DURATION: 1},
        blocking=True,
    )

    state = menuai.states.get(snooz_fan_entity_id)
    assert state.state == STATE_ON
    assert ATTR_ASSUMED_STATE not in state.attributes


@pytest.mark.parametrize("percentage", [1, 22, 50, 99, 100])
async def test_turn_on_with_percentage(
    menuai: menuai, snooz_fan_entity_id: str, percentage: int
) -> None:
    """Test turning on the device with a percentage."""
    await menuai.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: [snooz_fan_entity_id], fan.ATTR_PERCENTAGE: percentage},
        blocking=True,
    )

    state = menuai.states.get(snooz_fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_PERCENTAGE] == percentage
    assert ATTR_ASSUMED_STATE not in state.attributes


@pytest.mark.parametrize("percentage", [1, 22, 50, 99, 100])
async def test_set_percentage(
    menuai: menuai, snooz_fan_entity_id: str, percentage: int
) -> None:
    """Test setting the fan percentage."""
    await menuai.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_SET_PERCENTAGE,
        {ATTR_ENTITY_ID: [snooz_fan_entity_id], fan.ATTR_PERCENTAGE: percentage},
        blocking=True,
    )

    state = menuai.states.get(snooz_fan_entity_id)
    assert state.attributes[fan.ATTR_PERCENTAGE] == percentage
    assert ATTR_ASSUMED_STATE not in state.attributes


async def test_set_0_percentage_turns_off(
    menuai: menuai, snooz_fan_entity_id: str
) -> None:
    """Test turning off the device by setting the percentage/volume to 0."""
    await menuai.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: [snooz_fan_entity_id], fan.ATTR_PERCENTAGE: 66},
        blocking=True,
    )

    await menuai.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_SET_PERCENTAGE,
        {ATTR_ENTITY_ID: [snooz_fan_entity_id], fan.ATTR_PERCENTAGE: 0},
        blocking=True,
    )

    state = menuai.states.get(snooz_fan_entity_id)
    assert state.state == STATE_OFF
    # doesn't overwrite percentage when turning off
    assert state.attributes[fan.ATTR_PERCENTAGE] == 66
    assert ATTR_ASSUMED_STATE not in state.attributes


async def test_turn_off(menuai: menuai, snooz_fan_entity_id: str) -> None:
    """Test turning off the device."""
    await menuai.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: [snooz_fan_entity_id]},
        blocking=True,
    )

    state = menuai.states.get(snooz_fan_entity_id)
    assert state.state == STATE_OFF
    assert ATTR_ASSUMED_STATE not in state.attributes


async def test_transition_off(menuai: menuai, snooz_fan_entity_id: str) -> None:
    """Test transitioning off the device."""
    await menuai.services.async_call(
        DOMAIN,
        SERVICE_TRANSITION_OFF,
        {ATTR_ENTITY_ID: [snooz_fan_entity_id], ATTR_DURATION: 1},
        blocking=True,
    )

    state = menuai.states.get(snooz_fan_entity_id)
    assert state.state == STATE_OFF
    assert ATTR_ASSUMED_STATE not in state.attributes


async def test_push_events(
    menuai: menuai, mock_connected_snooz: SnoozFixture, snooz_fan_entity_id: str
) -> None:
    """Test state update events from snooz device."""
    mock_connected_snooz.device.trigger_state(SnoozDeviceState(False, 64))

    state = menuai.states.get(snooz_fan_entity_id)
    assert ATTR_ASSUMED_STATE not in state.attributes
    assert state.state == STATE_OFF
    assert state.attributes[fan.ATTR_PERCENTAGE] == 64

    mock_connected_snooz.device.trigger_state(SnoozDeviceState(True, 12))

    state = menuai.states.get(snooz_fan_entity_id)
    assert ATTR_ASSUMED_STATE not in state.attributes
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_PERCENTAGE] == 12

    mock_connected_snooz.device.trigger_disconnect()

    state = menuai.states.get(snooz_fan_entity_id)
    assert state.attributes[ATTR_ASSUMED_STATE] is True

    # Don't attempt to reconnect
    await mock_connected_snooz.device.async_disconnect()


async def test_restore_state(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Tests restoring entity state."""
    device = await create_mock_snooz(connected=False, initial_state=UnknownSnoozState)

    entry = await create_mock_snooz_config_entry(menuai, device)
    entity_id = get_fan_entity_id(menuai, device, entity_registry)

    # call service to store state
    await menuai.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: [entity_id], fan.ATTR_PERCENTAGE: 33},
        blocking=True,
    )

    # unload entry
    await menuai.config_entries.async_unload(entry.entry_id)

    state = menuai.states.get(entity_id)
    assert state.state == STATE_UNAVAILABLE

    # reload entry
    with (
        patch("menuai.components.snooz.SnoozDevice", return_value=device),
        patch(
            "menuai.components.snooz.async_ble_device_from_address",
            return_value=generate_ble_device(device.address, device.name),
        ),
    ):
        await menuai.config_entries.async_setup(entry.entry_id)

    # should match last known state
    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_PERCENTAGE] == 33
    assert state.attributes[ATTR_ASSUMED_STATE] is True


async def test_restore_unknown_state(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Tests restoring entity state that was unknown."""
    device = await create_mock_snooz(connected=False, initial_state=UnknownSnoozState)

    entry = await create_mock_snooz_config_entry(menuai, device)
    entity_id = get_fan_entity_id(menuai, device, entity_registry)

    # unload entry
    await menuai.config_entries.async_unload(entry.entry_id)

    state = menuai.states.get(entity_id)
    assert state.state == STATE_UNAVAILABLE

    # reload entry
    with (
        patch("menuai.components.snooz.SnoozDevice", return_value=device),
        patch(
            "menuai.components.snooz.async_ble_device_from_address",
            return_value=generate_ble_device(device.address, device.name),
        ),
    ):
        await menuai.config_entries.async_setup(entry.entry_id)

    # should match last known state
    state = menuai.states.get(entity_id)
    assert state.state == STATE_UNKNOWN


async def test_command_results(
    menuai: menuai, mock_connected_snooz: SnoozFixture, snooz_fan_entity_id: str
) -> None:
    """Test device command results."""
    mock_execute = Mock(spec=mock_connected_snooz.device.async_execute_command)

    mock_connected_snooz.device.async_execute_command = mock_execute

    mock_execute.return_value = SnoozCommandResult(
        SnoozCommandResultStatus.SUCCESSFUL, timedelta()
    )
    mock_connected_snooz.device.state = SnoozDeviceState(on=True, volume=56)

    await menuai.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: [snooz_fan_entity_id]},
        blocking=True,
    )

    state = menuai.states.get(snooz_fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_PERCENTAGE] == 56

    mock_execute.return_value = SnoozCommandResult(
        SnoozCommandResultStatus.CANCELLED, timedelta()
    )
    mock_connected_snooz.device.state = SnoozDeviceState(on=False, volume=15)

    await menuai.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: [snooz_fan_entity_id]},
        blocking=True,
    )

    # the device state shouldn't be written when cancelled
    state = menuai.states.get(snooz_fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_PERCENTAGE] == 56

    mock_execute.return_value = SnoozCommandResult(
        SnoozCommandResultStatus.UNEXPECTED_ERROR, timedelta()
    )

    with pytest.raises(menuaiError) as failure:
        await menuai.services.async_call(
            fan.DOMAIN,
            fan.SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: [snooz_fan_entity_id]},
            blocking=True,
        )

    assert failure.match("failed with status")


@pytest.fixture(name="snooz_fan_entity_id")
async def fixture_snooz_fan_entity_id(
    menuai: menuai,
    mock_connected_snooz: SnoozFixture,
    entity_registry: er.EntityRegistry,
) -> str:
    """Mock a Snooz fan entity and config entry."""

    return get_fan_entity_id(menuai, mock_connected_snooz.device, entity_registry)


def get_fan_entity_id(
    menuai: menuai, device: MockSnoozDevice, entity_registry: er.EntityRegistry
) -> str:
    """Get the entity ID for a mock device."""

    return entity_registry.async_get_entity_id(Platform.FAN, DOMAIN, device.address)
