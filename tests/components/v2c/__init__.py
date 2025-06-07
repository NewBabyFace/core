"""Tests for the V2C integration."""

from menuai.core import menuai

from tests.common import MockConfigEntry


async def init_integration(
    menuai: menuai, config_entry: MockConfigEntry
) -> MockConfigEntry:
    """Set up the V2C integration in MenuAI."""
    config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
