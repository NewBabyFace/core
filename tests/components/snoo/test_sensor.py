"""Test Snoo Sensors."""

from unittest.mock import AsyncMock

from menuai.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from menuai.core import menuai

from . import async_init_integration, find_update_callback
from .const import MOCK_SNOO_DATA


async def test_sensors(menuai: menuai, bypass_api: AsyncMock) -> None:
    """Test sensors and check test values are correctly set."""
    await async_init_integration(menuai)
    assert len(menuai.states.async_all("sensor")) == 2
    assert menuai.states.get("sensor.test_snoo_state").state == STATE_UNAVAILABLE
    assert menuai.states.get("sensor.test_snoo_time_left").state == STATE_UNAVAILABLE
    find_update_callback(bypass_api, "random_num")(MOCK_SNOO_DATA)
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all("sensor")) == 2
    assert menuai.states.get("sensor.test_snoo_state").state == "stop"
    assert menuai.states.get("sensor.test_snoo_time_left").state == STATE_UNKNOWN
