"""The pushbullet component."""

from __future__ import annotations

import logging

from pushbullet import InvalidKeyError, PushBullet, PushbulletError

from menuai.config_entries import ConfigEntry
from menuai.const import (
    CONF_API_KEY,
    CONF_NAME,
    EVENT_menuai_START,
    Platform,
)
from menuai.core import Event, menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers import config_validation as cv, discovery
from menuai.helpers.typing import ConfigType

from .api import PushBulletNotificationProvider
from .const import DATA_menuai_CONFIG, DOMAIN

PLATFORMS = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the pushbullet component."""

    menuai.data[DATA_menuai_CONFIG] = config
    return True


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up pushbullet from a config entry."""

    try:
        pushbullet = await menuai.async_add_executor_job(
            PushBullet, entry.data[CONF_API_KEY]
        )
    except InvalidKeyError:
        _LOGGER.error("Invalid API key for Pushbullet")
        return False
    except PushbulletError as err:
        raise ConfigEntryNotReady from err

    pb_provider = PushBulletNotificationProvider(menuai, pushbullet)
    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = pb_provider

    def start_listener(event: Event) -> None:
        """Start the listener thread."""
        _LOGGER.debug("Starting listener for pushbullet")
        pb_provider.start()

    menuai.bus.async_listen_once(EVENT_menuai_START, start_listener)

    menuai.async_create_task(
        discovery.async_load_platform(
            menuai,
            Platform.NOTIFY,
            DOMAIN,
            {CONF_NAME: entry.data[CONF_NAME], "entry_id": entry.entry_id},
            menuai.data[DATA_menuai_CONFIG],
        )
    )
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        pb_provider: PushBulletNotificationProvider = menuai.data[DOMAIN].pop(
            entry.entry_id
        )
        await menuai.async_add_executor_job(pb_provider.close)
    return unload_ok
