"""The Rainforest Eagle integration."""

from __future__ import annotations

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai

from .const import DOMAIN
from .coordinator import EagleDataCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Rainforest Eagle from a config entry."""
    coordinator = EagleDataCoordinator(menuai, entry)
    await coordinator.async_config_entry_first_refresh()
    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
