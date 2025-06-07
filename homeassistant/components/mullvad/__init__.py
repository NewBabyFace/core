"""The Mullvad VPN integration."""

import asyncio
from datetime import timedelta
import logging

from mullvad_api import MullvadAPI

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

PLATFORMS = [Platform.BINARY_SENSOR]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Mullvad VPN integration."""

    async def async_get_mullvad_api_data():
        async with asyncio.timeout(10):
            api = await menuai.async_add_executor_job(MullvadAPI)
            return api.data

    coordinator = DataUpdateCoordinator(
        menuai,
        logging.getLogger(__name__),
        config_entry=entry,
        name=DOMAIN,
        update_method=async_get_mullvad_api_data,
        update_interval=timedelta(minutes=1),
    )
    await coordinator.async_config_entry_first_refresh()

    menuai.data[DOMAIN] = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        del menuai.data[DOMAIN]

    return unload_ok
