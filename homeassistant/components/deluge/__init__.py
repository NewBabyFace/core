"""The Deluge integration."""

from __future__ import annotations

import logging
from ssl import SSLError

from deluge_client.client import DelugeRPCClient

from menuai.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    Platform,
)
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .const import CONF_WEB_PORT
from .coordinator import DelugeConfigEntry, DelugeDataUpdateCoordinator

PLATFORMS = [Platform.SENSOR, Platform.SWITCH]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: DelugeConfigEntry) -> bool:
    """Set up Deluge from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    api = await menuai.async_add_executor_job(
        DelugeRPCClient, host, port, username, password
    )
    api.web_port = entry.data[CONF_WEB_PORT]
    try:
        await menuai.async_add_executor_job(api.connect)
    except (ConnectionRefusedError, TimeoutError, SSLError) as ex:
        raise ConfigEntryNotReady("Connection to Deluge Daemon failed") from ex
    except Exception as ex:
        if type(ex).__name__ == "BadLoginError":
            raise ConfigEntryAuthFailed(
                "Credentials for Deluge client are not valid"
            ) from ex
        _LOGGER.error("Unknown error connecting to Deluge: %s", ex)

    coordinator = DelugeDataUpdateCoordinator(menuai, api, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: DelugeConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
