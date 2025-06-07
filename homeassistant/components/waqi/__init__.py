"""The World Air Quality Index (WAQI) integration."""

from __future__ import annotations

from aiowaqi import WAQIClient

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_API_KEY, Platform
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .coordinator import WAQIDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up World Air Quality Index (WAQI) from a config entry."""

    client = WAQIClient(session=async_get_clientsession(menuai))
    client.authenticate(entry.data[CONF_API_KEY])

    waqi_coordinator = WAQIDataUpdateCoordinator(menuai, entry, client)
    await waqi_coordinator.async_config_entry_first_refresh()
    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = waqi_coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
