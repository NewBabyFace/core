"""The sensor tests for the griddy platform."""

from unittest.mock import patch

from pydexcom import SessionError

from menuai.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from menuai.core import menuai
from menuai.helpers.entity_component import async_update_entity

from . import GLUCOSE_READING, init_integration


async def test_sensors(menuai: menuai) -> None:
    """Test we get sensor data."""
    await init_integration(menuai)

    test_username_glucose_value = menuai.states.get("sensor.test_username_glucose_value")
    assert test_username_glucose_value.state == str(GLUCOSE_READING.value)
    test_username_glucose_trend = menuai.states.get("sensor.test_username_glucose_trend")
    assert test_username_glucose_trend.state == GLUCOSE_READING.trend_description


async def test_sensors_unknown(menuai: menuai) -> None:
    """Test we handle sensor state unknown."""
    await init_integration(menuai)

    with patch(
        "menuai.components.dexcom.Dexcom.get_current_glucose_reading",
        return_value=None,
    ):
        await async_update_entity(menuai, "sensor.test_username_glucose_value")
        await async_update_entity(menuai, "sensor.test_username_glucose_trend")

    test_username_glucose_value = menuai.states.get("sensor.test_username_glucose_value")
    assert test_username_glucose_value.state == STATE_UNKNOWN
    test_username_glucose_trend = menuai.states.get("sensor.test_username_glucose_trend")
    assert test_username_glucose_trend.state == STATE_UNKNOWN


async def test_sensors_update_failed(menuai: menuai) -> None:
    """Test we handle sensor update failed."""
    await init_integration(menuai)

    with patch(
        "menuai.components.dexcom.Dexcom.get_current_glucose_reading",
        side_effect=SessionError,
    ):
        await async_update_entity(menuai, "sensor.test_username_glucose_value")
        await async_update_entity(menuai, "sensor.test_username_glucose_trend")

    test_username_glucose_value = menuai.states.get("sensor.test_username_glucose_value")
    assert test_username_glucose_value.state == STATE_UNAVAILABLE
    test_username_glucose_trend = menuai.states.get("sensor.test_username_glucose_trend")
    assert test_username_glucose_trend.state == STATE_UNAVAILABLE
