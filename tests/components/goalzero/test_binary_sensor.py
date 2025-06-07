"""Binary sensor tests for the Goalzero integration."""

from menuai.components.binary_sensor import BinarySensorDeviceClass
from menuai.components.goalzero.const import DEFAULT_NAME
from menuai.const import ATTR_DEVICE_CLASS, STATE_OFF, STATE_ON
from menuai.core import menuai

from . import async_init_integration

from tests.test_util.aiohttp import AiohttpClientMocker


async def test_binary_sensors(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test we get sensor data."""
    await async_init_integration(menuai, aioclient_mock)

    state = menuai.states.get(f"binary_sensor.{DEFAULT_NAME}_backlight")
    assert state.state == STATE_ON
    assert state.attributes.get(ATTR_DEVICE_CLASS) is None
    state = menuai.states.get(f"binary_sensor.{DEFAULT_NAME}_app_online")
    assert state.state == STATE_OFF
    assert (
        state.attributes.get(ATTR_DEVICE_CLASS) == BinarySensorDeviceClass.CONNECTIVITY
    )
    state = menuai.states.get(f"binary_sensor.{DEFAULT_NAME}_charging")
    assert state.state == STATE_OFF
    assert (
        state.attributes.get(ATTR_DEVICE_CLASS)
        == BinarySensorDeviceClass.BATTERY_CHARGING
    )
    state = menuai.states.get(f"binary_sensor.{DEFAULT_NAME}_input_detected")
    assert state.state == STATE_OFF
    assert state.attributes.get(ATTR_DEVICE_CLASS) == BinarySensorDeviceClass.POWER
