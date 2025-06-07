"""Binary sensor tests for the Skybell integration."""

from menuai.components.binary_sensor import BinarySensorDeviceClass
from menuai.const import ATTR_DEVICE_CLASS, STATE_OFF, STATE_ON
from menuai.core import menuai

from .conftest import async_init_integration


async def test_binary_sensors(menuai: menuai, connection) -> None:
    """Test we get sensor data."""
    await async_init_integration(menuai)

    state = menuai.states.get("binary_sensor.front_door_button")
    assert state.state == STATE_OFF
    assert state.attributes.get(ATTR_DEVICE_CLASS) == BinarySensorDeviceClass.OCCUPANCY
    state = menuai.states.get("binary_sensor.front_door_motion")
    assert state.state == STATE_ON
    assert state.attributes.get(ATTR_DEVICE_CLASS) == BinarySensorDeviceClass.MOTION
