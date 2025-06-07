"""The test for the Random binary sensor platform."""

from unittest.mock import patch

from menuai.core import menuai
from menuai.setup import async_setup_component


async def test_random_binary_sensor_on(menuai: menuai) -> None:
    """Test the Random binary sensor."""
    config = {"binary_sensor": {"platform": "random", "name": "test"}}

    with patch(
        "menuai.components.random.binary_sensor.getrandbits",
        return_value=1,
    ):
        assert await async_setup_component(
            menuai,
            "binary_sensor",
            config,
        )
        await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.test")

    assert state.state == "on"


async def test_random_binary_sensor_off(menuai: menuai) -> None:
    """Test the Random binary sensor."""
    config = {"binary_sensor": {"platform": "random", "name": "test"}}

    with patch(
        "menuai.components.random.binary_sensor.getrandbits",
        return_value=False,
    ):
        assert await async_setup_component(
            menuai,
            "binary_sensor",
            config,
        )
        await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.test")

    assert state.state == "off"
