"""The NYT Games integration."""

from __future__ import annotations

from nyt_games import NYTGamesClient

from menuai.const import CONF_TOKEN, Platform
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_create_clientsession

from .coordinator import NYTGamesConfigEntry, NYTGamesCoordinator

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
]


async def async_setup_entry(menuai: menuai, entry: NYTGamesConfigEntry) -> bool:
    """Set up NYTGames from a config entry."""

    client = NYTGamesClient(
        entry.data[CONF_TOKEN], session=async_create_clientsession(menuai)
    )

    coordinator = NYTGamesCoordinator(menuai, entry, client)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: NYTGamesConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
