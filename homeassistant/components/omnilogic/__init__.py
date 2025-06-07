"""The Omnilogic integration."""

import logging

from omnilogic import LoginException, OmniLogic, OmniLogicException

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_PASSWORD, CONF_USERNAME, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers import aiohttp_client

from .const import (
    CONF_SCAN_INTERVAL,
    COORDINATOR,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    OMNI_API,
)
from .coordinator import OmniLogicUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Omnilogic from a config entry."""

    conf = entry.data
    username = conf[CONF_USERNAME]
    password = conf[CONF_PASSWORD]

    polling_interval = conf.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    session = aiohttp_client.async_get_clientsession(menuai)

    api = OmniLogic(username, password, session)

    try:
        await api.connect()
        await api.get_telemetry_data()
    except LoginException as error:
        _LOGGER.error("Login Failed: %s", error)
        return False
    except OmniLogicException as error:
        _LOGGER.debug("OmniLogic API error: %s", error)
        raise ConfigEntryNotReady from error

    coordinator = OmniLogicUpdateCoordinator(
        menuai=menuai,
        api=api,
        name="Omnilogic",
        config_entry=entry,
        polling_interval=polling_interval,
    )
    await coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})
    menuai.data[DOMAIN][entry.entry_id] = {
        COORDINATOR: coordinator,
        OMNI_API: api,
    }

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
