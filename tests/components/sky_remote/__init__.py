"""Tests for the Sky Remote component."""

from menuai.core import menuai

from tests.common import MockConfigEntry


async def setup_mock_entry(menuai: menuai, entry: MockConfigEntry):
    """Initialize a mock config entry."""
    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)

    await menuai.async_block_till_done()
