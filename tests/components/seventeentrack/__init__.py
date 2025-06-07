"""Tests for the seventeentrack component."""

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory

from menuai.components.seventeentrack.const import DEFAULT_SCAN_INTERVAL
from menuai.core import menuai

from tests.common import MockConfigEntry, async_fire_time_changed


async def init_integration(
    menuai: menuai,
    config_entry: MockConfigEntry,
) -> None:
    """Set up the 17Track integration in MenuAI."""

    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()


async def goto_future(menuai: menuai, freezer: FrozenDateTimeFactory):
    """Move to future."""
    freezer.tick(DEFAULT_SCAN_INTERVAL + timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
