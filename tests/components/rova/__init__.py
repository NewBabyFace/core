"""Tests for the Rova component."""

from unittest.mock import patch

from menuai.const import Platform
from menuai.core import menuai

from tests.common import MockConfigEntry


async def setup_with_selected_platforms(
    menuai: menuai, entry: MockConfigEntry, platforms: list[Platform]
) -> None:
    """Set up the Rova integration with the selected platforms."""
    entry.add_to_menuai(menuai)
    with patch("menuai.components.rova.PLATFORMS", platforms):
        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()
