"""Tests for the buienradar component."""

from menuai.components.buienradar.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_LATITUDE, CONF_LONGITUDE
from menuai.core import menuai

from tests.common import MockConfigEntry
from tests.test_util.aiohttp import AiohttpClientMocker

TEST_LATITUDE = 51.5288504
TEST_LONGITUDE = 5.4002156


async def test_load_unload(
    aioclient_mock: AiohttpClientMocker, menuai: menuai
) -> None:
    """Test options flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_LATITUDE: TEST_LATITUDE,
            CONF_LONGITUDE: TEST_LONGITUDE,
        },
        unique_id=DOMAIN,
    )
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
