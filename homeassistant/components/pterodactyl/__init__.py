"""The Pterodactyl integration."""

from __future__ import annotations

from menuai.const import Platform
from menuai.core import menuai

from .coordinator import PterodactylConfigEntry, PterodactylCoordinator

_PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: PterodactylConfigEntry) -> bool:
    """Set up Pterodactyl from a config entry."""
    coordinator = PterodactylCoordinator(menuai, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True


async def async_unload_entry(
    menuai: menuai, entry: PterodactylConfigEntry
) -> bool:
    """Unload a Pterodactyl config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, _PLATFORMS)
