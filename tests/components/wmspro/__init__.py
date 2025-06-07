"""Tests for the wmspro integration."""

from menuai.core import menuai

from tests.common import MockConfigEntry


async def setup_config_entry(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
) -> bool:
    """Set up a config entry."""
    mock_config_entry.add_to_menuai(menuai)
    result = await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()
    return result
