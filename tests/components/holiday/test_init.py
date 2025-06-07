"""Tests for the Holiday integration."""

from menuai.components.holiday.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from tests.common import MockConfigEntry

MOCK_CONFIG_DATA = {
    "country": "Germany",
    "province": "BW",
}


async def test_unload_entry(menuai: menuai) -> None:
    """Test removing integration."""
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG_DATA)
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    state: ConfigEntryState = entry.state
    assert state is ConfigEntryState.NOT_LOADED
