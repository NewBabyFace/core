"""Support for Tibber."""

import logging

import aiohttp
import tibber

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_ACCESS_TOKEN, EVENT_menuai_STOP, Platform
from menuai.core import Event, menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers import config_validation as cv
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.typing import ConfigType
from menuai.util import dt as dt_util, ssl as ssl_util

from .const import DATA_menuai_CONFIG, DOMAIN
from .services import async_setup_services

PLATFORMS = [Platform.NOTIFY, Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the Tibber component."""

    menuai.data[DATA_menuai_CONFIG] = config

    async_setup_services(menuai)

    return True


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up a config entry."""

    tibber_connection = tibber.Tibber(
        access_token=entry.data[CONF_ACCESS_TOKEN],
        websession=async_get_clientsession(menuai),
        time_zone=dt_util.get_default_time_zone(),
        ssl=ssl_util.get_default_context(),
    )
    menuai.data[DOMAIN] = tibber_connection

    async def _close(event: Event) -> None:
        await tibber_connection.rt_disconnect()

    entry.async_on_unload(menuai.bus.async_listen_once(EVENT_menuai_STOP, _close))

    try:
        await tibber_connection.update_info()

    except (
        TimeoutError,
        aiohttp.ClientError,
        tibber.RetryableHttpExceptionError,
    ) as err:
        raise ConfigEntryNotReady("Unable to connect") from err
    except tibber.InvalidLoginError as exp:
        _LOGGER.error("Failed to login. %s", exp)
        return False
    except tibber.FatalHttpExceptionError:
        return False

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )
    if unload_ok:
        tibber_connection = menuai.data[DOMAIN]
        await tibber_connection.rt_disconnect()
    return unload_ok
