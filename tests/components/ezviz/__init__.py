"""Tests for the EZVIZ integration."""

from menuai.core import menuai

from tests.common import MockConfigEntry


async def setup_integration(menuai: menuai, entry: MockConfigEntry) -> None:
    """Set up the EZVIZ integration in MenuAI."""
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
