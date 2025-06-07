"""Provide tests for mysensors remote platform."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock, call

from mysensors.const_14 import SetReq
from mysensors.sensor import Sensor
import pytest

from menuai.components.remote import (
    ATTR_COMMAND,
    DOMAIN as REMOTE_DOMAIN,
    SERVICE_LEARN_COMMAND,
    SERVICE_SEND_COMMAND,
)
from menuai.const import (
    ATTR_BATTERY_LEVEL,
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from menuai.core import menuai


async def test_ir_transceiver(
    menuai: menuai,
    ir_transceiver: Sensor,
    receive_message: Callable[[str], None],
    transport_write: MagicMock,
) -> None:
    """Test an ir transceiver."""
    entity_id = "remote.ir_transceiver_1_1"

    state = menuai.states.get(entity_id)

    assert state
    assert state.state == "off"
    assert state.attributes[ATTR_BATTERY_LEVEL] == 0

    # Test turn on
    await menuai.services.async_call(
        REMOTE_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )

    assert transport_write.call_count == 2
    assert transport_write.call_args_list[0] == call("1;1;1;1;32;test_code\n")
    assert transport_write.call_args_list[1] == call("1;1;1;1;2;1\n")

    receive_message("1;1;1;0;32;test_code\n")
    receive_message("1;1;1;0;2;1\n")
    await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)

    assert state
    assert state.state == "on"

    transport_write.reset_mock()

    # Test send command
    await menuai.services.async_call(
        REMOTE_DOMAIN,
        SERVICE_SEND_COMMAND,
        {ATTR_ENTITY_ID: entity_id, ATTR_COMMAND: "new_code"},
        blocking=True,
    )

    assert transport_write.call_count == 1
    assert transport_write.call_args == call("1;1;1;1;32;new_code\n")

    receive_message("1;1;1;0;32;new_code\n")
    await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)

    assert state
    assert state.state == "on"

    transport_write.reset_mock()

    # Test learn command
    await menuai.services.async_call(
        REMOTE_DOMAIN,
        SERVICE_LEARN_COMMAND,
        {ATTR_ENTITY_ID: entity_id, ATTR_COMMAND: "learn_code"},
        blocking=True,
    )

    assert transport_write.call_count == 1
    assert transport_write.call_args == call("1;1;1;1;50;learn_code\n")

    receive_message("1;1;1;0;50;learn_code\n")
    await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)

    assert state
    assert state.state == "on"

    transport_write.reset_mock()

    # Test learn command with missing command parameter
    with pytest.raises(ValueError):
        await menuai.services.async_call(
            REMOTE_DOMAIN,
            SERVICE_LEARN_COMMAND,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )

    assert transport_write.call_count == 0

    transport_write.reset_mock()

    # Test turn off
    await menuai.services.async_call(
        REMOTE_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )

    assert transport_write.call_count == 1
    assert transport_write.call_args == call("1;1;1;1;2;0\n")

    receive_message("1;1;1;0;2;0\n")
    await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)

    assert state
    assert state.state == "off"

    transport_write.reset_mock()

    # Test turn on with new default code
    await menuai.services.async_call(
        REMOTE_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )

    assert transport_write.call_count == 2
    assert transport_write.call_args_list[0] == call("1;1;1;1;32;new_code\n")
    assert transport_write.call_args_list[1] == call("1;1;1;1;2;1\n")

    receive_message("1;1;1;0;32;new_code\n")
    receive_message("1;1;1;0;2;1\n")
    await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)

    assert state
    assert state.state == "on"

    # Test unknown state
    ir_transceiver.children[1].values.pop(SetReq.V_LIGHT)

    # Trigger state update
    receive_message("1;1;1;0;32;new_code\n")
    await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)

    assert state
    assert state.state == "unknown"
