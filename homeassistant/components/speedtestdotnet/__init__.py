"""Support for testing internet speed via Speedtest.net."""

from __future__ import annotations

from functools import partial

import speedtest

from menuai.config_entries import ConfigEntryState
from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers.start import async_at_started

from .coordinator import SpeedTestConfigEntry, SpeedTestDataCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(
    menuai: menuai, config_entry: SpeedTestConfigEntry
) -> bool:
    """Set up the Speedtest.net component."""
    try:
        api = await menuai.async_add_executor_job(
            partial(speedtest.Speedtest, secure=True)
        )
        coordinator = SpeedTestDataCoordinator(menuai, config_entry, api)
    except speedtest.SpeedtestException as err:
        raise ConfigEntryNotReady from err

    config_entry.runtime_data = coordinator

    async def _async_finish_startup(menuai: menuai) -> None:
        """Run this only when HA has finished its startup."""
        if config_entry.state is ConfigEntryState.LOADED:
            await coordinator.async_refresh()
        else:
            await coordinator.async_config_entry_first_refresh()

    # Don't start a speedtest during startup
    async_at_started(menuai, _async_finish_startup)

    await menuai.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    config_entry.async_on_unload(config_entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(
    menuai: menuai, config_entry: SpeedTestConfigEntry
) -> bool:
    """Unload SpeedTest Entry from config_entry."""
    return await menuai.config_entries.async_unload_platforms(config_entry, PLATFORMS)


async def update_listener(
    menuai: menuai, config_entry: SpeedTestConfigEntry
) -> None:
    """Handle options update."""
    await menuai.config_entries.async_reload(config_entry.entry_id)
