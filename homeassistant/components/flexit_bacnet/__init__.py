"""The Flexit Nordic (BACnet) integration."""

from __future__ import annotations

from menuai.const import Platform
from menuai.core import menuai

from .coordinator import FlexitConfigEntry, FlexitCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(menuai: menuai, entry: FlexitConfigEntry) -> bool:
    """Set up Flexit Nordic (BACnet) from a config entry."""

    coordinator = FlexitCoordinator(menuai, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: FlexitConfigEntry) -> bool:
    """Unload the Flexit Nordic (BACnet) config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
