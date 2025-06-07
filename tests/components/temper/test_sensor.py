"""The tests for the temper (USB temperature sensor) component."""

from datetime import timedelta
from unittest.mock import Mock, patch

from menuai.core import menuai
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import async_fire_time_changed


async def test_temperature_readback(menuai: menuai) -> None:
    """Test for reading sensors."""
    mock_temper_device = Mock()
    mock_temper_device.get_temperature.return_value = 12.3

    utcnow = dt_util.utcnow()

    with patch(
        "temperusb.temper.TemperHandler.get_devices",
        return_value=[mock_temper_device],
    ):
        await async_setup_component(
            menuai,
            "sensor",
            {"sensor": {"platform": "temper", "name": "mydevicename"}},
        )
        await menuai.async_block_till_done()

        async_fire_time_changed(menuai, utcnow + timedelta(seconds=70))
        await menuai.async_block_till_done(wait_background_tasks=True)

        temperature = menuai.states.get("sensor.mydevicename")
        assert temperature
        assert temperature.state == "12.3"
