"""The Adax integration."""

from __future__ import annotations

from menuai.const import Platform
from menuai.core import menuai

from .const import CONNECTION_TYPE, LOCAL
from .coordinator import AdaxCloudCoordinator, AdaxConfigEntry, AdaxLocalCoordinator

PLATFORMS = [Platform.CLIMATE, Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: AdaxConfigEntry) -> bool:
    """Set up Adax from a config entry."""
    if entry.data.get(CONNECTION_TYPE) == LOCAL:
        local_coordinator = AdaxLocalCoordinator(menuai, entry)
        entry.runtime_data = local_coordinator
    else:
        cloud_coordinator = AdaxCloudCoordinator(menuai, entry)
        entry.runtime_data = cloud_coordinator

    await entry.runtime_data.async_config_entry_first_refresh()

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: AdaxConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(
    menuai: menuai, config_entry: AdaxConfigEntry
) -> bool:
    """Migrate old entry."""
    # convert title and unique_id to string
    if config_entry.version == 1:
        if isinstance(config_entry.unique_id, int):
            menuai.config_entries.async_update_entry(  # type: ignore[unreachable]
                config_entry,
                unique_id=str(config_entry.unique_id),
                title=str(config_entry.title),
            )

    return True
