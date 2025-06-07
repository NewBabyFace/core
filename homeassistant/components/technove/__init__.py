"""The TechnoVE integration."""

from __future__ import annotations

from menuai.const import Platform
from menuai.core import menuai

from .coordinator import TechnoVEConfigEntry, TechnoVEDataUpdateCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.NUMBER, Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(menuai: menuai, entry: TechnoVEConfigEntry) -> bool:
    """Set up TechnoVE from a config entry."""
    coordinator = TechnoVEDataUpdateCoordinator(menuai, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: TechnoVEConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
