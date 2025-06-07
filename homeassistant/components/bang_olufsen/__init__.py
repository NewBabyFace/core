"""The Bang & Olufsen integration."""

from __future__ import annotations

from dataclasses import dataclass

from aiohttp.client_exceptions import (
    ClientConnectorError,
    ClientOSError,
    ServerTimeoutError,
    WSMessageTypeError,
)
from mozart_api.exceptions import ApiException
from mozart_api.mozart_client import MozartClient

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, CONF_MODEL, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers import device_registry as dr
from menuai.util.ssl import get_default_context

from .const import DOMAIN
from .websocket import BangOlufsenWebsocket


@dataclass
class BangOlufsenData:
    """Dataclass for API client and WebSocket client."""

    websocket: BangOlufsenWebsocket
    client: MozartClient


type BangOlufsenConfigEntry = ConfigEntry[BangOlufsenData]

PLATFORMS = [Platform.EVENT, Platform.MEDIA_PLAYER]


async def async_setup_entry(menuai: menuai, entry: BangOlufsenConfigEntry) -> bool:
    """Set up from a config entry."""

    # Remove casts to str
    assert entry.unique_id

    # Create device now as BangOlufsenWebsocket needs a device for debug logging, firing events etc.
    device_registry = dr.async_get(menuai)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.unique_id)},
        name=entry.title,
        model=entry.data[CONF_MODEL],
    )

    client = MozartClient(host=entry.data[CONF_HOST], ssl_context=get_default_context())

    # Check API and WebSocket connection
    try:
        await client.check_device_connection(True)
    except* (
        ClientConnectorError,
        ClientOSError,
        ServerTimeoutError,
        ApiException,
        TimeoutError,
        WSMessageTypeError,
    ) as error:
        await client.close_api_client()
        raise ConfigEntryNotReady(f"Unable to connect to {entry.title}") from error

    websocket = BangOlufsenWebsocket(menuai, entry, client)

    # Add the websocket and API client
    entry.runtime_data = BangOlufsenData(websocket, client)

    # Start WebSocket connection
    await client.connect_notifications(remote_control=True, reconnect=True)

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    menuai: menuai, entry: BangOlufsenConfigEntry
) -> bool:
    """Unload a config entry."""
    # Close the API client and WebSocket notification listener
    entry.runtime_data.client.disconnect_notifications()
    await entry.runtime_data.client.close_api_client()

    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
