"""The Rabbit Air integration."""

from __future__ import annotations

from rabbitair import Client, UdpClient

from menuai.components import zeroconf
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_ACCESS_TOKEN, CONF_HOST, Platform
from menuai.core import menuai

from .const import DOMAIN
from .coordinator import RabbitAirDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.FAN]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Rabbit Air from a config entry."""

    menuai.data.setdefault(DOMAIN, {})

    host: str = entry.data[CONF_HOST]
    token: str = entry.data[CONF_ACCESS_TOKEN]

    zeroconf_instance = await zeroconf.async_get_async_instance(menuai)
    device: Client = UdpClient(host, token, zeroconf=zeroconf_instance)

    coordinator = RabbitAirDataUpdateCoordinator(menuai, entry, device)

    await coordinator.async_config_entry_first_refresh()

    menuai.data[DOMAIN][entry.entry_id] = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def update_listener(menuai: menuai, entry: ConfigEntry) -> None:
    """Handle options update."""
    await menuai.config_entries.async_reload(entry.entry_id)
