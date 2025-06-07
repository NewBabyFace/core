"""Tests for the Linear Garage Door integration."""

from unittest.mock import patch

from menuai.const import Platform
from menuai.core import menuai

from tests.common import MockConfigEntry


async def setup_integration(
    menuai: menuai, config_entry: MockConfigEntry, platforms: list[Platform]
) -> None:
    """Fixture for setting up the component."""
    config_entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.linear_garage_door.PLATFORMS",
        platforms,
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
