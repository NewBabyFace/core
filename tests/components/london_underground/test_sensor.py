"""The tests for the london_underground platform."""

from london_tube_status import API_URL

from menuai.components.london_underground.const import CONF_LINE, DOMAIN
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import async_load_fixture
from tests.test_util.aiohttp import AiohttpClientMocker

VALID_CONFIG = {
    "sensor": {"platform": "london_underground", CONF_LINE: ["Metropolitan"]}
}


async def test_valid_state(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test for operational london_underground sensor with proper attributes."""
    aioclient_mock.get(
        API_URL,
        text=await async_load_fixture(menuai, "line_status.json", DOMAIN),
    )

    assert await async_setup_component(menuai, "sensor", VALID_CONFIG)
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.metropolitan")
    assert state
    assert state.state == "Good Service"
    assert state.attributes == {
        "Description": "Nothing to report",
        "attribution": "Powered by TfL Open Data",
        "friendly_name": "Metropolitan",
        "icon": "mdi:subway",
    }
