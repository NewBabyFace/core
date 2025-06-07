"""Support for Open-Meteo."""

from __future__ import annotations

from menuai.const import Platform
from menuai.core import menuai

from .coordinator import OpenMeteoConfigEntry, OpenMeteoDataUpdateCoordinator

PLATFORMS = [Platform.WEATHER]


async def async_setup_entry(menuai: menuai, entry: OpenMeteoConfigEntry) -> bool:
    """Set up Open-Meteo from a config entry."""

    coordinator = OpenMeteoDataUpdateCoordinator(menuai, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: OpenMeteoConfigEntry) -> bool:
    """Unload Open-Meteo config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
