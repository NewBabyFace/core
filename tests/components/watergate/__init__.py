"""Tests for the Watergate integration."""

from menuai.core import menuai


async def init_integration(menuai: menuai, mock_entry) -> None:
    """Set up the Watergate integration in MenuAI."""
    mock_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(mock_entry.entry_id)
    await menuai.async_block_till_done()
