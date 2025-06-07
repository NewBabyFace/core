"""The SensorPush Cloud integration."""

from __future__ import annotations

from menuai.const import Platform
from menuai.core import menuai

from .coordinator import SensorPushCloudConfigEntry, SensorPushCloudCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(
    menuai: menuai, entry: SensorPushCloudConfigEntry
) -> bool:
    """Set up SensorPush Cloud from a config entry."""
    coordinator = SensorPushCloudCoordinator(menuai, entry)
    entry.runtime_data = coordinator
    await coordinator.async_config_entry_first_refresh()
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    menuai: menuai, entry: SensorPushCloudConfigEntry
) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
