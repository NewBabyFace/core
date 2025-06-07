"""The OpenGarage integration."""

from __future__ import annotations

import opengarage

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, CONF_PORT, CONF_VERIFY_SSL, Platform
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_DEVICE_KEY, DOMAIN
from .coordinator import OpenGarageDataUpdateCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.COVER, Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up OpenGarage from a config entry."""
    open_garage_connection = opengarage.OpenGarage(
        f"{entry.data[CONF_HOST]}:{entry.data[CONF_PORT]}",
        entry.data[CONF_DEVICE_KEY],
        entry.data[CONF_VERIFY_SSL],
        async_get_clientsession(menuai),
    )
    open_garage_data_coordinator = OpenGarageDataUpdateCoordinator(
        menuai, entry, open_garage_connection
    )
    await open_garage_data_coordinator.async_config_entry_first_refresh()
    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = open_garage_data_coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
