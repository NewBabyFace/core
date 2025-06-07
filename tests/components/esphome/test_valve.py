"""Test ESPHome valves."""

from unittest.mock import call

from aioesphomeapi import (
    APIClient,
    ValveInfo,
    ValveOperation,
    ValveState as ESPHomeValveState,
)

from menuai.components.valve import (
    ATTR_CURRENT_POSITION,
    ATTR_POSITION,
    DOMAIN as VALVE_DOMAIN,
    SERVICE_CLOSE_VALVE,
    SERVICE_OPEN_VALVE,
    SERVICE_SET_VALVE_POSITION,
    SERVICE_STOP_VALVE,
    ValveState,
)
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai

from .conftest import MockESPHomeDeviceType


async def test_valve_entity(
    menuai: menuai,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:
    """Test a generic valve entity."""
    entity_info = [
        ValveInfo(
            object_id="myvalve",
            key=1,
            name="my valve",
            unique_id="my_valve",
            supports_position=True,
            supports_stop=True,
        )
    ]
    states = [
        ESPHomeValveState(
            key=1,
            position=0.5,
            current_operation=ValveOperation.IS_OPENING,
        )
    ]
    user_service = []
    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        entity_info=entity_info,
        user_service=user_service,
        states=states,
    )
    state = menuai.states.get("valve.test_myvalve")
    assert state is not None
    assert state.state == ValveState.OPENING
    assert state.attributes[ATTR_CURRENT_POSITION] == 50

    await menuai.services.async_call(
        VALVE_DOMAIN,
        SERVICE_CLOSE_VALVE,
        {ATTR_ENTITY_ID: "valve.test_myvalve"},
        blocking=True,
    )
    mock_client.valve_command.assert_has_calls([call(key=1, position=0.0)])
    mock_client.valve_command.reset_mock()

    await menuai.services.async_call(
        VALVE_DOMAIN,
        SERVICE_OPEN_VALVE,
        {ATTR_ENTITY_ID: "valve.test_myvalve"},
        blocking=True,
    )
    mock_client.valve_command.assert_has_calls([call(key=1, position=1.0)])
    mock_client.valve_command.reset_mock()

    await menuai.services.async_call(
        VALVE_DOMAIN,
        SERVICE_SET_VALVE_POSITION,
        {ATTR_ENTITY_ID: "valve.test_myvalve", ATTR_POSITION: 50},
        blocking=True,
    )
    mock_client.valve_command.assert_has_calls([call(key=1, position=0.5)])
    mock_client.valve_command.reset_mock()

    await menuai.services.async_call(
        VALVE_DOMAIN,
        SERVICE_STOP_VALVE,
        {ATTR_ENTITY_ID: "valve.test_myvalve"},
        blocking=True,
    )
    mock_client.valve_command.assert_has_calls([call(key=1, stop=True)])
    mock_client.valve_command.reset_mock()

    mock_device.set_state(
        ESPHomeValveState(key=1, position=0.0, current_operation=ValveOperation.IDLE)
    )
    await menuai.async_block_till_done()
    state = menuai.states.get("valve.test_myvalve")
    assert state is not None
    assert state.state == ValveState.CLOSED

    mock_device.set_state(
        ESPHomeValveState(
            key=1, position=0.5, current_operation=ValveOperation.IS_CLOSING
        )
    )
    await menuai.async_block_till_done()
    state = menuai.states.get("valve.test_myvalve")
    assert state is not None
    assert state.state == ValveState.CLOSING

    mock_device.set_state(
        ESPHomeValveState(key=1, position=1.0, current_operation=ValveOperation.IDLE)
    )
    await menuai.async_block_till_done()
    state = menuai.states.get("valve.test_myvalve")
    assert state is not None
    assert state.state == ValveState.OPEN


async def test_valve_entity_without_position(
    menuai: menuai,
    mock_client: APIClient,
    mock_esphome_device: MockESPHomeDeviceType,
) -> None:
    """Test a generic valve entity without position or stop."""
    entity_info = [
        ValveInfo(
            object_id="myvalve",
            key=1,
            name="my valve",
            unique_id="my_valve",
            supports_position=False,
            supports_stop=False,
        )
    ]
    states = [
        ESPHomeValveState(
            key=1,
            position=0.5,
            current_operation=ValveOperation.IS_OPENING,
        )
    ]
    user_service = []
    mock_device = await mock_esphome_device(
        mock_client=mock_client,
        entity_info=entity_info,
        user_service=user_service,
        states=states,
    )
    state = menuai.states.get("valve.test_myvalve")
    assert state is not None
    assert state.state == ValveState.OPENING
    assert ATTR_CURRENT_POSITION not in state.attributes

    await menuai.services.async_call(
        VALVE_DOMAIN,
        SERVICE_CLOSE_VALVE,
        {ATTR_ENTITY_ID: "valve.test_myvalve"},
        blocking=True,
    )
    mock_client.valve_command.assert_has_calls([call(key=1, position=0.0)])
    mock_client.valve_command.reset_mock()

    await menuai.services.async_call(
        VALVE_DOMAIN,
        SERVICE_OPEN_VALVE,
        {ATTR_ENTITY_ID: "valve.test_myvalve"},
        blocking=True,
    )
    mock_client.valve_command.assert_has_calls([call(key=1, position=1.0)])
    mock_client.valve_command.reset_mock()

    mock_device.set_state(
        ESPHomeValveState(key=1, position=0.0, current_operation=ValveOperation.IDLE)
    )
    await menuai.async_block_till_done()
    state = menuai.states.get("valve.test_myvalve")
    assert state is not None
    assert state.state == ValveState.CLOSED
