"""Provide tests for mysensors switch platform."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock, call

from mysensors.sensor import Sensor

from menuai.components.switch import DOMAIN as SWITCH_DOMAIN
from menuai.const import ATTR_BATTERY_LEVEL
from menuai.core import menuai


async def test_relay_node(
    menuai: menuai,
    relay_node: Sensor,
    receive_message: Callable[[str], None],
    transport_write: MagicMock,
) -> None:
    """Test a relay node."""
    entity_id = "switch.relay_node_1_1"

    state = menuai.states.get(entity_id)

    assert state
    assert state.state == "off"
    assert state.attributes[ATTR_BATTERY_LEVEL] == 0

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        "turn_on",
        {"entity_id": entity_id},
        blocking=True,
    )

    assert transport_write.call_count == 1
    assert transport_write.call_args == call("1;1;1;1;2;1\n")

    receive_message("1;1;1;0;2;1\n")
    await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)

    assert state
    assert state.state == "on"

    transport_write.reset_mock()

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        "turn_off",
        {"entity_id": entity_id},
        blocking=True,
    )

    assert transport_write.call_count == 1
    assert transport_write.call_args == call("1;1;1;1;2;0\n")

    receive_message("1;1;1;0;2;0\n")
    await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)

    assert state
    assert state.state == "off"
