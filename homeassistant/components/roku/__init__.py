"""Support for Roku."""

from __future__ import annotations

from menuai.const import Platform
from menuai.core import menuai

from .coordinator import RokuConfigEntry, RokuDataUpdateCoordinator

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.MEDIA_PLAYER,
    Platform.REMOTE,
    Platform.SELECT,
    Platform.SENSOR,
]


async def async_setup_entry(menuai: menuai, entry: RokuConfigEntry) -> bool:
    """Set up Roku from a config entry."""
    coordinator = RokuDataUpdateCoordinator(menuai, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(menuai: menuai, entry: RokuConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(menuai: menuai, entry: RokuConfigEntry) -> None:
    """Reload the config entry when it changed."""
    await menuai.config_entries.async_reload(entry.entry_id)
