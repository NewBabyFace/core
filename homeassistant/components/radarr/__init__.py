"""The Radarr component."""

from __future__ import annotations

from dataclasses import fields

from aiopyarr.models.host_configuration import PyArrHostConfiguration
from aiopyarr.radarr_client import RadarrClient

from menuai.const import CONF_API_KEY, CONF_URL, CONF_VERIFY_SSL, Platform
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession

from .coordinator import (
    CalendarUpdateCoordinator,
    DiskSpaceDataUpdateCoordinator,
    HealthDataUpdateCoordinator,
    MoviesDataUpdateCoordinator,
    QueueDataUpdateCoordinator,
    RadarrConfigEntry,
    RadarrData,
    RadarrDataUpdateCoordinator,
    StatusDataUpdateCoordinator,
)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.CALENDAR, Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: RadarrConfigEntry) -> bool:
    """Set up Radarr from a config entry."""
    host_configuration = PyArrHostConfiguration(
        api_token=entry.data[CONF_API_KEY],
        verify_ssl=entry.data[CONF_VERIFY_SSL],
        url=entry.data[CONF_URL],
    )
    radarr = RadarrClient(
        host_configuration=host_configuration,
        session=async_get_clientsession(menuai, entry.data[CONF_VERIFY_SSL]),
    )
    data = RadarrData(
        calendar=CalendarUpdateCoordinator(menuai, entry, host_configuration, radarr),
        disk_space=DiskSpaceDataUpdateCoordinator(
            menuai, entry, host_configuration, radarr
        ),
        health=HealthDataUpdateCoordinator(menuai, entry, host_configuration, radarr),
        movie=MoviesDataUpdateCoordinator(menuai, entry, host_configuration, radarr),
        queue=QueueDataUpdateCoordinator(menuai, entry, host_configuration, radarr),
        status=StatusDataUpdateCoordinator(menuai, entry, host_configuration, radarr),
    )
    for field in fields(data):
        coordinator: RadarrDataUpdateCoordinator = getattr(data, field.name)
        # Movie update can take a while depending on Radarr database size
        if field.name == "movie":
            entry.async_create_background_task(
                menuai,
                coordinator.async_config_entry_first_refresh(),
                "radarr.movie-coordinator-first-refresh",
            )
            continue
        await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = data
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: RadarrConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
