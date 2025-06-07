"""The syncthru component."""

from __future__ import annotations

from pysyncthru import SyncThruAPINotSupported

from menuai.const import Platform
from menuai.core import menuai

from .coordinator import SyncThruConfigEntry, SyncthruCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: SyncThruConfigEntry) -> bool:
    """Set up config entry."""

    coordinator = SyncthruCoordinator(menuai, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    if isinstance(coordinator.last_exception, SyncThruAPINotSupported):
        # this means that the printer does not support the syncthru JSON API
        # and the config should simply be discarded
        return False

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: SyncThruConfigEntry) -> bool:
    """Unload the config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
