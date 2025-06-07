"""The syncthing integration."""

import asyncio
import logging

import aiosyncthing

from menuai.config_entries import ConfigEntry
from menuai.const import (
    CONF_TOKEN,
    CONF_URL,
    CONF_VERIFY_SSL,
    EVENT_menuai_STOP,
    Platform,
)
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers.dispatcher import async_dispatcher_send

from .const import (
    DOMAIN,
    EVENTS,
    RECONNECT_INTERVAL,
    SERVER_AVAILABLE,
    SERVER_UNAVAILABLE,
)

PLATFORMS = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up syncthing from a config entry."""
    data = entry.data

    if DOMAIN not in menuai.data:
        menuai.data[DOMAIN] = {}

    client = aiosyncthing.Syncthing(
        data[CONF_TOKEN],
        url=data[CONF_URL],
        verify_ssl=data[CONF_VERIFY_SSL],
    )

    try:
        status = await client.system.status()
    except aiosyncthing.exceptions.SyncthingError as exception:
        await client.close()
        raise ConfigEntryNotReady from exception

    server_id = status["myID"]

    syncthing = SyncthingClient(menuai, client, server_id)
    syncthing.subscribe()
    menuai.data[DOMAIN][entry.entry_id] = syncthing

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def cancel_listen_task(_):
        await syncthing.unsubscribe()

    entry.async_on_unload(
        menuai.bus.async_listen_once(EVENT_menuai_STOP, cancel_listen_task)
    )

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        syncthing = menuai.data[DOMAIN].pop(entry.entry_id)
        await syncthing.unsubscribe()

    return unload_ok


class SyncthingClient:
    """A Syncthing client."""

    def __init__(self, menuai, client, server_id):
        """Initialize the client."""
        self._menuai = menuai
        self._client = client
        self._server_id = server_id
        self._listen_task = None

    @property
    def server_id(self):
        """Get server id."""
        return self._server_id

    @property
    def url(self):
        """Get server URL."""
        return self._client.url

    @property
    def database(self):
        """Get database namespace client."""
        return self._client.database

    @property
    def system(self):
        """Get system namespace client."""
        return self._client.system

    def subscribe(self):
        """Start event listener coroutine."""
        self._listen_task = asyncio.create_task(self._listen())

    async def unsubscribe(self):
        """Stop event listener coroutine."""
        if self._listen_task:
            self._listen_task.cancel()
        await self._client.close()

    async def _listen(self):
        """Listen to Syncthing events."""
        events = self._client.events
        server_was_unavailable = False
        while True:
            if await self._server_available():
                if server_was_unavailable:
                    _LOGGER.warning(
                        "The syncthing server '%s' is back online", self._client.url
                    )
                    async_dispatcher_send(
                        self._menuai, f"{SERVER_AVAILABLE}-{self._server_id}"
                    )
                    server_was_unavailable = False
            else:
                await asyncio.sleep(RECONNECT_INTERVAL.total_seconds())
                continue
            try:
                async for event in events.listen():
                    if events.last_seen_id == 0:
                        continue  # skipping historical events from the first batch
                    if event["type"] not in EVENTS:
                        continue

                    signal_name = EVENTS[event["type"]]
                    folder = None
                    if "folder" in event["data"]:
                        folder = event["data"]["folder"]
                    else:  # A workaround, some events store folder id under `id` key
                        folder = event["data"]["id"]
                    async_dispatcher_send(
                        self._menuai,
                        f"{signal_name}-{self._server_id}-{folder}",
                        event,
                    )
            except aiosyncthing.exceptions.SyncthingError:
                _LOGGER.warning(
                    (
                        "The syncthing server '%s' is not available. Sleeping %i"
                        " seconds and retrying"
                    ),
                    self._client.url,
                    RECONNECT_INTERVAL.total_seconds(),
                )
                async_dispatcher_send(
                    self._menuai, f"{SERVER_UNAVAILABLE}-{self._server_id}"
                )
                await asyncio.sleep(RECONNECT_INTERVAL.total_seconds())
                server_was_unavailable = True
                continue

    async def _server_available(self):
        try:
            await self._client.system.ping()
        except aiosyncthing.exceptions.SyncthingError:
            return False

        return True
