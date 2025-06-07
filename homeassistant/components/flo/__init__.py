"""The flo integration."""

import asyncio
import logging

from aioflo import async_get_api
from aioflo.errors import RequestError

from menuai.const import CONF_PASSWORD, CONF_USERNAME, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers.aiohttp_client import async_get_clientsession

from .coordinator import FloConfigEntry, FloDeviceDataUpdateCoordinator, FloRuntimeData

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(menuai: menuai, entry: FloConfigEntry) -> bool:
    """Set up flo from a config entry."""
    session = async_get_clientsession(menuai)
    try:
        client = await async_get_api(
            entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD], session=session
        )
    except RequestError as err:
        raise ConfigEntryNotReady from err

    user_info = await client.user.get_info(include_location_info=True)

    _LOGGER.debug("Flo user information with locations: %s", user_info)

    devices = [
        FloDeviceDataUpdateCoordinator(
            menuai, entry, client, location["id"], device["id"]
        )
        for location in user_info["locations"]
        for device in location["devices"]
    ]

    tasks = [device.async_refresh() for device in devices]
    await asyncio.gather(*tasks)

    entry.runtime_data = FloRuntimeData(client=client, devices=devices)
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: FloConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
