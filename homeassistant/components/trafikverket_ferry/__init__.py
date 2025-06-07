"""The trafikverket_ferry component."""

from __future__ import annotations

from menuai.config_entries import ConfigEntry
from menuai.core import menuai

from .const import PLATFORMS
from .coordinator import TVDataUpdateCoordinator

TVFerryConfigEntry = ConfigEntry[TVDataUpdateCoordinator]


async def async_setup_entry(menuai: menuai, entry: TVFerryConfigEntry) -> bool:
    """Set up Trafikverket Ferry from a config entry."""

    coordinator = TVDataUpdateCoordinator(menuai, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: TVFerryConfigEntry) -> bool:
    """Unload Trafikverket Ferry config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
