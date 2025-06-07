"""Support for the Moehlenhoff Alpha2."""

from __future__ import annotations

from moehlenhoff_alpha2 import Alpha2Base

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, Platform
from menuai.core import menuai

from .const import DOMAIN
from .coordinator import Alpha2BaseCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.CLIMATE, Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    base = Alpha2Base(entry.data[CONF_HOST])
    coordinator = Alpha2BaseCoordinator(menuai, entry, base)

    await coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})
    menuai.data[DOMAIN][entry.entry_id] = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok and entry.entry_id in menuai.data[DOMAIN]:
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def update_listener(menuai: menuai, entry: ConfigEntry) -> None:
    """Handle options update."""
    await menuai.config_entries.async_reload(entry.entry_id)
