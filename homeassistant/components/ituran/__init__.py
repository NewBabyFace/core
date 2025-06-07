"""The Ituran integration."""

from __future__ import annotations

from menuai.const import Platform
from menuai.core import menuai

from .coordinator import IturanConfigEntry, IturanDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.DEVICE_TRACKER,
    Platform.SENSOR,
]


async def async_setup_entry(menuai: menuai, entry: IturanConfigEntry) -> bool:
    """Set up Ituran from a config entry."""

    coordinator = IturanDataUpdateCoordinator(menuai, entry=entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: IturanConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
