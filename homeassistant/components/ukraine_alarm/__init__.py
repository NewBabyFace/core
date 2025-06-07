"""The ukraine_alarm component."""

from __future__ import annotations

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, PLATFORMS
from .coordinator import UkraineAlarmDataUpdateCoordinator


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Ukraine Alarm as config entry."""
    websession = async_get_clientsession(menuai)

    coordinator = UkraineAlarmDataUpdateCoordinator(menuai, entry, websession)
    await coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
