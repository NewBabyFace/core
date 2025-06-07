"""Tests for the bsblan integration."""

from unittest.mock import patch

from menuai.const import Platform
from menuai.core import menuai

from tests.common import MockConfigEntry


async def setup_with_selected_platforms(
    menuai: menuai, config_entry: MockConfigEntry, platforms: list[Platform]
) -> None:
    """Set up the BSBLAN integration with the selected platforms."""
    config_entry.add_to_menuai(menuai)
    with patch("menuai.components.bsblan.PLATFORMS", platforms):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
