"""The Devialet integration."""

from __future__ import annotations

from devialet import DevialetApi

from menuai.const import CONF_HOST, Platform
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession

from .coordinator import DevialetConfigEntry, DevialetCoordinator

PLATFORMS = [Platform.MEDIA_PLAYER]


async def async_setup_entry(menuai: menuai, entry: DevialetConfigEntry) -> bool:
    """Set up Devialet from a config entry."""
    session = async_get_clientsession(menuai)
    client = DevialetApi(entry.data[CONF_HOST], session)
    coordinator = DevialetCoordinator(menuai, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: DevialetConfigEntry) -> bool:
    """Unload Devialet config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
