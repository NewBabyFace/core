"""The BleBox devices integration."""

import logging

from blebox_uniapi.box import Box
from blebox_uniapi.error import Error
from blebox_uniapi.session import ApiHost

from menuai.config_entries import ConfigEntry
from menuai.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    Platform,
)
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady

from .const import DEFAULT_SETUP_TIMEOUT
from .helpers import get_maybe_authenticated_session

type BleBoxConfigEntry = ConfigEntry[Box]

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.COVER,
    Platform.LIGHT,
    Platform.SENSOR,
    Platform.SWITCH,
]

PARALLEL_UPDATES = 0


async def async_setup_entry(menuai: menuai, entry: BleBoxConfigEntry) -> bool:
    """Set up BleBox devices from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]

    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)

    timeout = DEFAULT_SETUP_TIMEOUT

    websession = get_maybe_authenticated_session(menuai, password, username)

    api_host = ApiHost(host, port, timeout, websession, menuai.loop)

    try:
        product = await Box.async_from_host(api_host)
    except Error as ex:
        _LOGGER.error("Identify failed at %s:%d (%s)", api_host.host, api_host.port, ex)
        raise ConfigEntryNotReady from ex

    entry.runtime_data = product

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: BleBoxConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
