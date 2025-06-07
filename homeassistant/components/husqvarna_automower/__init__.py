"""The Husqvarna Automower integration."""

import logging

from aioautomower.session import AutomowerSession
from aiohttp import ClientResponseError

from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from menuai.helpers import aiohttp_client, config_entry_oauth2_flow
from menuai.util import dt as dt_util

from . import api
from .coordinator import AutomowerConfigEntry, AutomowerDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CALENDAR,
    Platform.DEVICE_TRACKER,
    Platform.LAWN_MOWER,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(menuai: menuai, entry: AutomowerConfigEntry) -> bool:
    """Set up this integration using UI."""
    implementation = (
        await config_entry_oauth2_flow.async_get_config_entry_implementation(
            menuai, entry
        )
    )
    session = config_entry_oauth2_flow.OAuth2Session(menuai, entry, implementation)
    api_api = api.AsyncConfigEntryAuth(
        aiohttp_client.async_get_clientsession(menuai),
        session,
    )
    time_zone_str = str(dt_util.DEFAULT_TIME_ZONE)
    automower_api = AutomowerSession(
        api_api,
        await dt_util.async_get_time_zone(time_zone_str),
    )
    try:
        await api_api.async_get_access_token()
    except ClientResponseError as err:
        if 400 <= err.status < 500:
            raise ConfigEntryAuthFailed from err
        raise ConfigEntryNotReady from err

    if "amc:api" not in entry.data["token"]["scope"]:
        # We raise ConfigEntryAuthFailed here because the websocket can't be used
        # without the scope. So only polling would be possible.
        raise ConfigEntryAuthFailed

    coordinator = AutomowerDataUpdateCoordinator(menuai, entry, automower_api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    entry.async_create_background_task(
        menuai,
        coordinator.client_listen(menuai, entry, automower_api),
        "websocket_task",
    )

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: AutomowerConfigEntry) -> bool:
    """Handle unload of an entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
