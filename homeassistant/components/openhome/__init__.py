"""The openhome component."""

import logging

import aiohttp
from async_upnp_client.client import UpnpError
from openhomedevice.device import Device

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers import config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.MEDIA_PLAYER, Platform.UPDATE]

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_unload_entry(menuai: menuai, config_entry: ConfigEntry) -> bool:
    """Cleanup before removing config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )
    menuai.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
) -> bool:
    """Set up the configuration config entry."""
    _LOGGER.debug("Setting up config entry: %s", config_entry.unique_id)

    device = await menuai.async_add_executor_job(Device, config_entry.data[CONF_HOST])

    try:
        await device.init()
    except (TimeoutError, aiohttp.ClientError, UpnpError) as exc:
        raise ConfigEntryNotReady from exc

    _LOGGER.debug("Initialised device: %s", device.uuid())

    menuai.data.setdefault(DOMAIN, {})[config_entry.entry_id] = device

    await menuai.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True
