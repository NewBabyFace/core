"""Support for freedompro."""

from __future__ import annotations

from typing import Final

from menuai.const import Platform
from menuai.core import menuai

from .coordinator import FreedomproConfigEntry, FreedomproDataUpdateCoordinator

PLATFORMS: Final[list[Platform]] = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.COVER,
    Platform.FAN,
    Platform.LIGHT,
    Platform.LOCK,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(menuai: menuai, entry: FreedomproConfigEntry) -> bool:
    """Set up Freedompro from a config entry."""
    coordinator = FreedomproDataUpdateCoordinator(menuai, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.async_on_unload(entry.add_update_listener(update_listener))

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: FreedomproConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async def update_listener(
    menuai: menuai, config_entry: FreedomproConfigEntry
) -> None:
    """Update listener."""
    await menuai.config_entries.async_reload(config_entry.entry_id)
