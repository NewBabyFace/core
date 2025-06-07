"""The Volumio integration."""

from pyvolumio import CannotConnectError, Volumio

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, CONF_PORT, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers.aiohttp_client import async_get_clientsession

from .const import DATA_INFO, DATA_VOLUMIO, DOMAIN

PLATFORMS = [Platform.MEDIA_PLAYER]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Volumio from a config entry."""

    volumio = Volumio(
        entry.data[CONF_HOST], entry.data[CONF_PORT], async_get_clientsession(menuai)
    )
    try:
        info = await volumio.get_system_version()
    except CannotConnectError as error:
        raise ConfigEntryNotReady from error

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        DATA_VOLUMIO: volumio,
        DATA_INFO: info,
    }

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
