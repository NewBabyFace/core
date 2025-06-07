"""Tests for the Suez Water integration."""

from menuai.core import menuai

from tests.common import MockConfigEntry


async def setup_integration(
    menuai: menuai, mock_config_entry: MockConfigEntry
) -> None:
    """Init suez water integration."""
    mock_config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()
