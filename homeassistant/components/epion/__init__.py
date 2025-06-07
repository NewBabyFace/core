"""The Epion integration."""

from __future__ import annotations

from epion import Epion

from menuai.const import CONF_API_KEY, Platform
from menuai.core import menuai

from .coordinator import EpionConfigEntry, EpionCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: EpionConfigEntry) -> bool:
    """Set up the Epion coordinator from a config entry."""
    api = Epion(entry.data[CONF_API_KEY])
    coordinator = EpionCoordinator(menuai, entry, api)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: EpionConfigEntry) -> bool:
    """Unload Epion config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
