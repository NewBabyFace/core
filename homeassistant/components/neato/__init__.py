"""Support for Neato botvac connected vacuum cleaners."""

import logging

import aiohttp
from pybotvac import Account
from pybotvac.exceptions import NeatoException

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_TOKEN, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from menuai.helpers import config_entry_oauth2_flow

from . import api
from .const import NEATO_DOMAIN, NEATO_LOGIN
from .hub import NeatoHub

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.BUTTON,
    Platform.CAMERA,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.VACUUM,
]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up config entry."""
    menuai.data.setdefault(NEATO_DOMAIN, {})
    if CONF_TOKEN not in entry.data:
        raise ConfigEntryAuthFailed

    implementation = (
        await config_entry_oauth2_flow.async_get_config_entry_implementation(
            menuai, entry
        )
    )

    session = config_entry_oauth2_flow.OAuth2Session(menuai, entry, implementation)
    try:
        await session.async_ensure_token_valid()
    except aiohttp.ClientResponseError as ex:
        _LOGGER.debug("API error: %s (%s)", ex.code, ex.message)
        if ex.code in (401, 403):
            raise ConfigEntryAuthFailed("Token not valid, trigger renewal") from ex
        raise ConfigEntryNotReady from ex

    neato_session = api.ConfigEntryAuth(menuai, entry, implementation)
    menuai.data[NEATO_DOMAIN][entry.entry_id] = neato_session
    hub = NeatoHub(menuai, Account(neato_session))

    await hub.async_update_entry_unique_id(entry)

    try:
        await menuai.async_add_executor_job(hub.update_robots)
    except NeatoException as ex:
        _LOGGER.debug("Failed to connect to Neato API")
        raise ConfigEntryNotReady from ex

    menuai.data[NEATO_LOGIN] = hub

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        menuai.data[NEATO_DOMAIN].pop(entry.entry_id)

    return unload_ok
