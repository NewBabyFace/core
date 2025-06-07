"""The Epic Games Store integration."""

from __future__ import annotations

from menuai.const import Platform
from menuai.core import menuai

from .coordinator import EGSCalendarUpdateCoordinator, EGSConfigEntry

PLATFORMS: list[Platform] = [
    Platform.CALENDAR,
]


async def async_setup_entry(menuai: menuai, entry: EGSConfigEntry) -> bool:
    """Set up Epic Games Store from a config entry."""

    coordinator = EGSCalendarUpdateCoordinator(menuai, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: EGSConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
