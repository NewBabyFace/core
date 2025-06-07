"""The SiteSage Emonitor integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from aioemonitor import Emonitor
from aioemonitor.monitor import EmonitorStatus

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, Platform
from menuai.core import menuai
from menuai.helpers import aiohttp_client
from menuai.helpers.update_coordinator import DataUpdateCoordinator

type EmonitorConfigEntry = ConfigEntry[DataUpdateCoordinator[EmonitorStatus]]

_LOGGER = logging.getLogger(__name__)

DEFAULT_UPDATE_RATE = 60

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: EmonitorConfigEntry) -> bool:
    """Set up SiteSage Emonitor from a config entry."""
    session = aiohttp_client.async_get_clientsession(menuai)
    emonitor = Emonitor(entry.data[CONF_HOST], session)

    coordinator = DataUpdateCoordinator[EmonitorStatus](
        menuai,
        _LOGGER,
        config_entry=entry,
        name=entry.title,
        update_method=emonitor.async_get_status,
        update_interval=timedelta(seconds=DEFAULT_UPDATE_RATE),
        always_update=False,
    )

    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: EmonitorConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


def name_short_mac(short_mac):
    """Name from short mac."""
    return f"Emonitor {short_mac}"
