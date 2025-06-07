"""Provide tests for mysensors binary sensor platform."""

from __future__ import annotations

from collections.abc import Callable

from mysensors.sensor import Sensor

from menuai.components.binary_sensor import BinarySensorDeviceClass
from menuai.const import ATTR_BATTERY_LEVEL, ATTR_DEVICE_CLASS
from menuai.core import menuai


async def test_door_sensor(
    menuai: menuai,
    door_sensor: Sensor,
    receive_message: Callable[[str], None],
) -> None:
    """Test a door sensor."""
    entity_id = "binary_sensor.door_sensor_1_1"

    state = menuai.states.get(entity_id)

    assert state
    assert state.state == "off"
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.DOOR
    assert state.attributes[ATTR_BATTERY_LEVEL] == 0

    receive_message("1;1;1;0;16;1\n")
    await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)

    assert state
    assert state.state == "on"

    receive_message("1;1;1;0;16;0\n")
    await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)

    assert state
    assert state.state == "off"
