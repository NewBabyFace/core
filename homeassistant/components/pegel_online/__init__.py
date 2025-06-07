"""The PEGELONLINE component."""

from __future__ import annotations

import logging

from aiopegelonline import PegelOnline
from aiopegelonline.const import CONNECT_ERRORS

from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_STATION
from .coordinator import PegelOnlineConfigEntry, PegelOnlineDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: PegelOnlineConfigEntry) -> bool:
    """Set up PEGELONLINE entry."""
    station_uuid = entry.data[CONF_STATION]

    _LOGGER.debug("Setting up station with uuid %s", station_uuid)

    api = PegelOnline(async_get_clientsession(menuai))
    try:
        station = await api.async_get_station_details(station_uuid)
    except CONNECT_ERRORS as err:
        raise ConfigEntryNotReady("Failed to connect") from err

    coordinator = PegelOnlineDataUpdateCoordinator(menuai, entry, api, station)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    menuai: menuai, entry: PegelOnlineConfigEntry
) -> bool:
    """Unload PEGELONLINE entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
