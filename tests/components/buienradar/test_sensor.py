"""The tests for the Buienradar sensor platform."""

from http import HTTPStatus

from menuai.components.buienradar.const import DOMAIN
from menuai.const import CONF_LATITUDE, CONF_LONGITUDE
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry
from tests.test_util.aiohttp import AiohttpClientMocker

TEST_LONGITUDE = 51.5288504
TEST_LATITUDE = 5.4002156

CONDITIONS = ["stationname", "temperature"]
TEST_CFG_DATA = {CONF_LATITUDE: TEST_LATITUDE, CONF_LONGITUDE: TEST_LONGITUDE}


async def test_smoke_test_setup_component(
    aioclient_mock: AiohttpClientMocker,
    menuai: menuai,
    entity_registry: er.EntityRegistry,
) -> None:
    """Smoke test for successfully set-up with default config."""
    aioclient_mock.get(
        "https://data.buienradar.nl/2.0/feed/json", status=HTTPStatus.NOT_FOUND
    )
    mock_entry = MockConfigEntry(domain=DOMAIN, unique_id="TEST_ID", data=TEST_CFG_DATA)

    mock_entry.add_to_menuai(menuai)

    for cond in CONDITIONS:
        entity_registry.async_get_or_create(
            domain="sensor",
            platform="buienradar",
            unique_id=f"{TEST_LATITUDE:2.6f}{TEST_LONGITUDE:2.6f}{cond}",
            config_entry=mock_entry,
            original_name=f"Buienradar {cond}",
        )
    await menuai.async_block_till_done()

    await menuai.config_entries.async_setup(mock_entry.entry_id)
    await menuai.async_block_till_done()

    for cond in CONDITIONS:
        state = menuai.states.get(f"sensor.buienradar_5_40021651_528850{cond}")
        assert state.state == "unknown"
