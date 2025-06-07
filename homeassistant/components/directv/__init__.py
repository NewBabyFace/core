"""The DirecTV integration."""

from __future__ import annotations

from datetime import timedelta

from directv import DIRECTV, DIRECTVError

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers.aiohttp_client import async_get_clientsession

PLATFORMS = [Platform.MEDIA_PLAYER, Platform.REMOTE]
SCAN_INTERVAL = timedelta(seconds=30)


type DirecTVConfigEntry = ConfigEntry[DIRECTV]


async def async_setup_entry(menuai: menuai, entry: DirecTVConfigEntry) -> bool:
    """Set up DirecTV from a config entry."""
    dtv = DIRECTV(entry.data[CONF_HOST], session=async_get_clientsession(menuai))

    try:
        await dtv.update()
    except DIRECTVError as err:
        raise ConfigEntryNotReady from err

    entry.runtime_data = dtv

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: DirecTVConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
