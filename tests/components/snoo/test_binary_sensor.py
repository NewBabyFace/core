"""Test Snoo Binary Sensors."""

from unittest.mock import AsyncMock

from menuai.const import STATE_ON, STATE_UNAVAILABLE
from menuai.core import menuai

from . import async_init_integration, find_update_callback
from .const import MOCK_SNOO_DATA


async def test_binary_sensors(menuai: menuai, bypass_api: AsyncMock) -> None:
    """Test binary sensors and check test values are correctly set."""
    await async_init_integration(menuai)
    assert len(menuai.states.async_all("binary_sensor")) == 2
    assert (
        menuai.states.get("binary_sensor.test_snoo_left_safety_clip").state
        == STATE_UNAVAILABLE
    )
    assert (
        menuai.states.get("binary_sensor.test_snoo_right_safety_clip").state
        == STATE_UNAVAILABLE
    )
    find_update_callback(bypass_api, "random_num")(MOCK_SNOO_DATA)
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all("binary_sensor")) == 2
    assert menuai.states.get("binary_sensor.test_snoo_left_safety_clip").state == STATE_ON
    assert (
        menuai.states.get("binary_sensor.test_snoo_right_safety_clip").state == STATE_ON
    )
