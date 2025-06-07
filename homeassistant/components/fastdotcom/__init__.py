"""Support for testing internet speed via Fast.com."""

from __future__ import annotations

import logging

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.helpers.start import async_at_started

from .const import PLATFORMS
from .coordinator import FastdotcomConfigEntry, FastdotcomDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: FastdotcomConfigEntry) -> bool:
    """Set up Fast.com from a config entry."""
    coordinator = FastdotcomDataUpdateCoordinator(menuai, entry)
    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    async def _async_finish_startup(menuai: menuai) -> None:
        """Run this only when HA has finished its startup."""
        if entry.state == ConfigEntryState.LOADED:
            await coordinator.async_refresh()
        else:
            await coordinator.async_config_entry_first_refresh()

    # Don't start a speedtest during startup, this will slow down the overall startup dramatically
    async_at_started(menuai, _async_finish_startup)
    return True


async def async_unload_entry(menuai: menuai, entry: FastdotcomConfigEntry) -> bool:
    """Unload Fast.com config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
