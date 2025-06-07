"""The brunt component."""

from __future__ import annotations

from menuai.core import menuai

from .const import PLATFORMS
from .coordinator import BruntConfigEntry, BruntCoordinator


async def async_setup_entry(menuai: menuai, entry: BruntConfigEntry) -> bool:
    """Set up Brunt using config flow."""
    coordinator = BruntCoordinator(menuai, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: BruntConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
