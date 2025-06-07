"""Define tests for the The Things Network."""

from menuai.core import menuai


async def init_integration(menuai: menuai, config_entry) -> None:
    """Mock TTNClient."""
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
