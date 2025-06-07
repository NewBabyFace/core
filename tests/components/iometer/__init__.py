"""Tests for the IOmeter integration."""

from unittest.mock import patch

from menuai.const import Platform
from menuai.core import menuai

from tests.common import MockConfigEntry


async def setup_platform(
    menuai: menuai, config_entry: MockConfigEntry, platforms: list[Platform]
) -> MockConfigEntry:
    """Fixture for setting up the IOmeter platform."""
    config_entry.add_to_menuai(menuai)

    with patch("menuai.components.iometer.PLATFORMS", platforms):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
