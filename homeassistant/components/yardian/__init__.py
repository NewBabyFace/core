"""The Yardian integration."""

from __future__ import annotations

from pyyardian import AsyncYardianClient

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_ACCESS_TOKEN, CONF_HOST, Platform
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .coordinator import YardianUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SWITCH]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Yardian from a config entry."""

    host = entry.data[CONF_HOST]
    access_token = entry.data[CONF_ACCESS_TOKEN]

    controller = AsyncYardianClient(async_get_clientsession(menuai), host, access_token)
    coordinator = YardianUpdateCoordinator(menuai, entry, controller)
    await coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data.get(DOMAIN, {}).pop(entry.entry_id, None)

    return unload_ok
