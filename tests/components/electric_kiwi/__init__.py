"""Tests for the Electric Kiwi integration."""

from menuai.core import menuai

from tests.common import MockConfigEntry


async def init_integration(menuai: menuai, entry: MockConfigEntry) -> None:
    """Fixture for setting up the integration with args."""
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
