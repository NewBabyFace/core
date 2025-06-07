"""The tests for the Open Hardware Monitor platform."""

import requests_mock

from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import async_load_fixture


async def test_setup(menuai: menuai, requests_mock: requests_mock.Mocker) -> None:
    """Test for successfully setting up the platform."""
    config = {
        "sensor": {
            "platform": "openhardwaremonitor",
            "host": "localhost",
            "port": 8085,
        }
    }

    requests_mock.get(
        "http://localhost:8085/data.json",
        text=await async_load_fixture(
            menuai, "openhardwaremonitor.json", "openhardwaremonitor"
        ),
    )

    await async_setup_component(menuai, "sensor", config)
    await menuai.async_block_till_done()

    entities = menuai.states.async_entity_ids("sensor")
    assert len(entities) == 38

    state = menuai.states.get("sensor.test_pc_intel_core_i7_7700_temperatures_cpu_core_1")

    assert state is not None
    assert state.state == "31.0"

    state = menuai.states.get("sensor.test_pc_intel_core_i7_7700_temperatures_cpu_core_2")

    assert state is not None
    assert state.state == "30.0"
