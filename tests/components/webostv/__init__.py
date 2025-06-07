"""Tests for the LG webOS TV integration."""

from menuai.components.webostv.const import DOMAIN
from menuai.const import CONF_CLIENT_SECRET, CONF_HOST
from menuai.core import menuai

from .const import CLIENT_KEY, FAKE_UUID, HOST, TV_NAME

from tests.common import MockConfigEntry


async def setup_webostv(
    menuai: menuai, unique_id: str | None = FAKE_UUID
) -> MockConfigEntry:
    """Initialize webostv and media_player for tests."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: HOST,
            CONF_CLIENT_SECRET: CLIENT_KEY,
        },
        title=TV_NAME,
        unique_id=unique_id,
    )
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    return entry
