"""The launch_library component."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import TypedDict

from pylaunches import PyLaunches, PyLaunchesError
from pylaunches.types import Launch, StarshipResponse

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]


class LaunchLibraryData(TypedDict):
    """Typed dict representation of data returned from pylaunches."""

    upcoming_launches: list[Launch]
    starship_events: StarshipResponse


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""

    menuai.data.setdefault(DOMAIN, {})

    session = async_get_clientsession(menuai)
    launches = PyLaunches(session)

    async def async_update() -> LaunchLibraryData:
        try:
            return LaunchLibraryData(
                upcoming_launches=await launches.launch_upcoming(
                    filters={"limit": 1, "hide_recent_previous": "True"},
                ),
                starship_events=await launches.dashboard_starship(),
            )
        except PyLaunchesError as ex:
            raise UpdateFailed(ex) from ex

    coordinator = DataUpdateCoordinator(
        menuai,
        _LOGGER,
        config_entry=entry,
        name=DOMAIN,
        update_method=async_update,
        update_interval=timedelta(hours=1),
    )

    await coordinator.async_config_entry_first_refresh()

    menuai.data[DOMAIN] = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        del menuai.data[DOMAIN]
    return unload_ok
