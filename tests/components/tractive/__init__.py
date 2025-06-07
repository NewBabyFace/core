"""Tests for the tractive integration."""

from unittest.mock import patch

from menuai.core import menuai

from tests.common import MockConfigEntry


async def init_integration(
    menuai: menuai, entry: MockConfigEntry
) -> MockConfigEntry:
    """Set up the Tractive integration in MenuAI."""
    entry.add_to_menuai(menuai)

    with patch("menuai.components.tractive.TractiveClient._listen"):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()
