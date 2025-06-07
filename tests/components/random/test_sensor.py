"""The test for the random number sensor platform."""

from menuai.core import menuai
from menuai.setup import async_setup_component


async def test_random_sensor(menuai: menuai) -> None:
    """Test the Random number sensor."""
    config = {
        "sensor": {
            "platform": "random",
            "name": "test",
            "minimum": 10,
            "maximum": 20,
        }
    }

    assert await async_setup_component(
        menuai,
        "sensor",
        config,
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.test")

    assert int(state.state) <= config["sensor"]["maximum"]
    assert int(state.state) >= config["sensor"]["minimum"]
