"""The tests for the buienradar weather component."""

from http import HTTPStatus

from menuai.components.buienradar.const import DOMAIN
from menuai.const import CONF_LATITUDE, CONF_LONGITUDE
from menuai.core import menuai

from tests.common import MockConfigEntry
from tests.test_util.aiohttp import AiohttpClientMocker

TEST_CFG_DATA = {CONF_LATITUDE: 51.5288504, CONF_LONGITUDE: 5.4002156}


async def test_smoke_test_setup_component(
    aioclient_mock: AiohttpClientMocker, menuai: menuai
) -> None:
    """Smoke test for successfully set-up with default config."""
    aioclient_mock.get(
        "https://data.buienradar.nl/2.0/feed/json", status=HTTPStatus.NOT_FOUND
    )
    mock_entry = MockConfigEntry(domain=DOMAIN, unique_id="TEST_ID", data=TEST_CFG_DATA)

    mock_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(mock_entry.entry_id)
    await menuai.async_block_till_done()

    state = menuai.states.get("weather.buienradar")
    assert state.state == "unknown"
