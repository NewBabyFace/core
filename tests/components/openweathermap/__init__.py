"""Shared utilities for OpenWeatherMap tests."""

from unittest.mock import patch

from menuai.config_entries import ConfigEntryState
from menuai.const import Platform
from menuai.core import menuai

from tests.common import MockConfigEntry


async def setup_platform(
    menuai: menuai,
    config_entry: MockConfigEntry,
    platforms: list[Platform],
):
    """Set up the OpenWeatherMap platform."""
    config_entry.add_to_menuai(menuai)
    with (
        patch("menuai.components.openweathermap.PLATFORMS", platforms),
    ):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
        assert config_entry.state is ConfigEntryState.LOADED
