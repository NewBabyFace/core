"""Tests for Deutscher Wetterdienst (DWD) Weather Warnings."""

from menuai.core import menuai

from tests.common import MockConfigEntry


async def init_integration(
    menuai: menuai, entry: MockConfigEntry
) -> MockConfigEntry:
    """Set up the integration based on the config entry."""
    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    return entry
