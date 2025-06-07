"""Tests for the Cookidoo integration."""

from menuai.core import menuai

from tests.common import MockConfigEntry


async def setup_integration(
    menuai: menuai,
    cookidoo_config_entry: MockConfigEntry,
) -> None:
    """Mock setup of the cookidoo integration."""
    cookidoo_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(cookidoo_config_entry.entry_id)
    await menuai.async_block_till_done()
