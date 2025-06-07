"""Tests for the StreamLabs integration."""

from menuai.core import menuai
from menuai.util.unit_system import US_CUSTOMARY_SYSTEM

from tests.common import MockConfigEntry


async def setup_integration(menuai: menuai, config_entry: MockConfigEntry) -> None:
    """Fixture for setting up the component."""
    config_entry.add_to_menuai(menuai)

    menuai.config.units = US_CUSTOMARY_SYSTEM

    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
