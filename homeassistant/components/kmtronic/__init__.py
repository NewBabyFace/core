"""The kmtronic integration."""

import asyncio
from datetime import timedelta
import logging

import aiohttp
from pykmtronic.auth import Auth
from pykmtronic.hub import KMTronicHubAPI

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from menuai.core import menuai
from menuai.helpers import aiohttp_client
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DATA_COORDINATOR, DATA_HUB, DOMAIN, MANUFACTURER, UPDATE_LISTENER

PLATFORMS = [Platform.SWITCH]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up kmtronic from a config entry."""
    session = aiohttp_client.async_get_clientsession(menuai)
    auth = Auth(
        session,
        f"http://{entry.data[CONF_HOST]}",
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )
    hub = KMTronicHubAPI(auth)

    async def async_update_data():
        try:
            async with asyncio.timeout(10):
                await hub.async_update_relays()
        except aiohttp.client_exceptions.ClientResponseError as err:
            raise UpdateFailed(f"Wrong credentials: {err}") from err
        except aiohttp.client_exceptions.ClientConnectorError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    coordinator = DataUpdateCoordinator(
        menuai,
        _LOGGER,
        config_entry=entry,
        name=f"{MANUFACTURER} {hub.name}",
        update_method=async_update_data,
        update_interval=timedelta(seconds=30),
    )
    await coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})
    menuai.data[DOMAIN][entry.entry_id] = {
        DATA_HUB: hub,
        DATA_COORDINATOR: coordinator,
    }

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    update_listener = entry.add_update_listener(async_update_options)
    menuai.data[DOMAIN][entry.entry_id][UPDATE_LISTENER] = update_listener

    return True


async def async_update_options(menuai: menuai, config_entry: ConfigEntry) -> None:
    """Update options."""
    await menuai.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        update_listener = menuai.data[DOMAIN][entry.entry_id][UPDATE_LISTENER]
        update_listener()
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
