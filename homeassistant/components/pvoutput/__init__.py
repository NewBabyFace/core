"""The PVOutput integration."""

from __future__ import annotations

from menuai.config_entries import ConfigEntry
from menuai.core import menuai

from .const import DOMAIN, PLATFORMS
from .coordinator import PVOutputDataUpdateCoordinator


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up PVOutput from a config entry."""
    coordinator = PVOutputDataUpdateCoordinator(menuai, entry)
    await coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload PVOutput config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        del menuai.data[DOMAIN][entry.entry_id]
    return unload_ok
