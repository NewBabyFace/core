"""Tests for the Velbus component."""

from menuai.components.velbus import VelbusConfigEntry
from menuai.core import menuai


async def init_integration(
    menuai: menuai,
    config_entry: VelbusConfigEntry,
) -> None:
    """Load the Velbus integration."""
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
