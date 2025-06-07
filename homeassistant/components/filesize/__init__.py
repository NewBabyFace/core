"""The filesize component."""

from __future__ import annotations

from menuai.core import menuai

from .const import PLATFORMS
from .coordinator import FileSizeConfigEntry, FileSizeCoordinator


async def async_setup_entry(menuai: menuai, entry: FileSizeConfigEntry) -> bool:
    """Set up from a config entry."""
    coordinator = FileSizeCoordinator(menuai, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: FileSizeConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
