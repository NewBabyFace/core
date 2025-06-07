"""Tests for the Ondilo ICO integration."""

from unittest.mock import MagicMock

from menuai.core import menuai

from tests.common import MockConfigEntry


async def setup_integration(
    menuai: menuai, config_entry: MockConfigEntry, mock_ondilo_client: MagicMock
) -> None:
    """Fixture for setting up the component."""
    config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
