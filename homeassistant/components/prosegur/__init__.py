"""The Prosegur Alarm integration."""

import logging

from pyprosegur.auth import Auth

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_COUNTRY, CONF_PASSWORD, CONF_USERNAME, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from menuai.helpers import aiohttp_client

from .const import DOMAIN

PLATFORMS = [Platform.ALARM_CONTROL_PANEL, Platform.CAMERA]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Prosegur Alarm from a config entry."""
    try:
        session = aiohttp_client.async_get_clientsession(menuai)
        menuai.data.setdefault(DOMAIN, {})
        menuai.data[DOMAIN][entry.entry_id] = Auth(
            session,
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
            entry.data[CONF_COUNTRY],
        )
        await menuai.data[DOMAIN][entry.entry_id].login()

    except ConnectionRefusedError as error:
        _LOGGER.error("Configured credential are invalid, %s", error)

        raise ConfigEntryAuthFailed from error

    except ConnectionError as error:
        _LOGGER.error("Could not connect with Prosegur backend: %s", error)
        raise ConfigEntryNotReady from error

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
