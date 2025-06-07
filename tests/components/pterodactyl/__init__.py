"""Tests for the Pterodactyl integration."""

from menuai.core import menuai

from tests.common import MockConfigEntry


async def setup_integration(
    menuai: menuai, mock_config_entry: MockConfigEntry
) -> MockConfigEntry:
    """Set up Pterodactyl mock config entry."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    return mock_config_entry
