"""The Balboa Spa Client integration."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging

from pybalboa import SpaClient

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers.event import async_track_time_interval
from menuai.util import dt as dt_util

from .const import CONF_SYNC_TIME, DEFAULT_SYNC_TIME

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.EVENT,
    Platform.FAN,
    Platform.LIGHT,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.TIME,
]

KEEP_ALIVE_INTERVAL = timedelta(minutes=1)
SYNC_TIME_INTERVAL = timedelta(hours=1)

type BalboaConfigEntry = ConfigEntry[SpaClient]


async def async_setup_entry(menuai: menuai, entry: BalboaConfigEntry) -> bool:
    """Set up Balboa Spa from a config entry."""
    host = entry.data[CONF_HOST]

    _LOGGER.debug("Attempting to connect to %s", host)
    spa = SpaClient(host)
    if not await spa.connect():
        _LOGGER.error("Failed to connect to spa at %s", host)
        raise ConfigEntryNotReady("Unable to connect")
    if not await spa.async_configuration_loaded():
        _LOGGER.error("Failed to get spa info at %s", host)
        raise ConfigEntryNotReady("Unable to configure")

    entry.runtime_data = spa

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    await async_setup_time_sync(menuai, entry)
    entry.async_on_unload(entry.add_update_listener(update_listener))
    entry.async_on_unload(spa.disconnect)

    return True


async def async_unload_entry(menuai: menuai, entry: BalboaConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async def update_listener(menuai: menuai, entry: BalboaConfigEntry) -> None:
    """Handle options update."""
    await menuai.config_entries.async_reload(entry.entry_id)


async def async_setup_time_sync(menuai: menuai, entry: BalboaConfigEntry) -> None:
    """Set up the time sync."""
    if not entry.options.get(CONF_SYNC_TIME, DEFAULT_SYNC_TIME):
        return

    _LOGGER.debug("Setting up daily time sync")
    spa = entry.runtime_data

    async def sync_time(now: datetime) -> None:
        now = dt_util.as_local(now)
        if (now.hour, now.minute) != (spa.time_hour, spa.time_minute):
            _LOGGER.debug("Syncing time with MenuAI")
            await spa.set_time(now.hour, now.minute)

    await sync_time(dt_util.utcnow())
    entry.async_on_unload(
        async_track_time_interval(menuai, sync_time, SYNC_TIME_INTERVAL)
    )
