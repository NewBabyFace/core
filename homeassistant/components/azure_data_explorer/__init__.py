"""The Azure Data Explorer integration."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
import json
import logging

from azure.kusto.data.exceptions import KustoAuthenticationError, KustoServiceError
import voluptuous as vol

from menuai.config_entries import ConfigEntry
from menuai.const import MATCH_ALL
from menuai.core import Event, menuai, State
from menuai.exceptions import ConfigEntryError
from menuai.helpers.entityfilter import FILTER_SCHEMA, EntityFilter
from menuai.helpers.event import async_call_later
from menuai.helpers.json import ExtendedJSONEncoder
from menuai.helpers.typing import ConfigType
from menuai.util.dt import utcnow
from menuai.util.menuai_dict import menuaiKey

from .client import AzureDataExplorerClient
from .const import (
    CONF_APP_REG_SECRET,
    CONF_FILTER,
    CONF_SEND_INTERVAL,
    DEFAULT_MAX_DELAY,
    DOMAIN,
    FILTER_STATES,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_FILTER, default={}): FILTER_SCHEMA,
            },
        )
    },
    extra=vol.ALLOW_EXTRA,
)
DATA_COMPONENT: menuaiKey[EntityFilter] = menuaiKey(DOMAIN)


# fixtures for both init and config flow tests
@dataclass
class FilterTest:
    """Class for capturing a filter test."""

    entity_id: str
    expect_called: bool


async def async_setup(menuai: menuai, yaml_config: ConfigType) -> bool:
    """Activate ADX component from yaml.

    Adds an empty filter to menuai data.
    Tries to get a filter from yaml, if present set to menuai data.
    """
    if DOMAIN in yaml_config:
        menuai.data[DATA_COMPONENT] = yaml_config[DOMAIN].pop(CONF_FILTER)
    else:
        menuai.data[DATA_COMPONENT] = FILTER_SCHEMA({})

    return True


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Do the setup based on the config entry and the filter from yaml."""
    adx = AzureDataExplorer(menuai, entry)
    try:
        await adx.test_connection()
    except KustoServiceError as exp:
        raise ConfigEntryError(
            "Could not find Azure Data Explorer database or table"
        ) from exp
    except KustoAuthenticationError:
        return False

    entry.async_on_unload(adx.async_stop)
    await adx.async_start()
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return True


class AzureDataExplorer:
    """A event handler class for Azure Data Explorer."""

    def __init__(
        self,
        menuai: menuai,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the listener."""

        self.menuai = menuai
        self._entry = entry
        self._entities_filter = menuai.data[DATA_COMPONENT]

        self._client = AzureDataExplorerClient(entry.data)

        self._send_interval = entry.options[CONF_SEND_INTERVAL]
        self._client_secret = entry.data[CONF_APP_REG_SECRET]
        self._max_delay = DEFAULT_MAX_DELAY

        self._shutdown = False
        self._queue: asyncio.Queue[tuple[datetime, State]] = asyncio.Queue()
        self._listener_remover: Callable[[], None] | None = None
        self._next_send_remover: Callable[[], None] | None = None

    async def async_start(self) -> None:
        """Start the component.

        This register the listener and
        schedules the first send.
        """

        self._listener_remover = self.menuai.bus.async_listen(
            MATCH_ALL, self.async_listen
        )
        self._schedule_next_send()

    async def async_stop(self) -> None:
        """Shut down the ADX by queueing None, calling send, join queue."""
        if self._next_send_remover:
            self._next_send_remover()
        if self._listener_remover:
            self._listener_remover()
        self._shutdown = True
        await self.async_send(None)

    async def test_connection(self) -> None:
        """Test the connection to the Azure Data Explorer service."""
        await self.menuai.async_add_executor_job(self._client.test_connection)

    def _schedule_next_send(self) -> None:
        """Schedule the next send."""
        if not self._shutdown:
            if self._next_send_remover:
                self._next_send_remover()
            self._next_send_remover = async_call_later(
                self.menuai, self._send_interval, self.async_send
            )

    async def async_listen(self, event: Event) -> None:
        """Listen for new messages on the bus and queue them for ADX."""
        if state := event.data.get("new_state"):
            await self._queue.put((event.time_fired, state))

    async def async_send(self, _) -> None:
        """Write preprocessed events to Azure Data Explorer."""

        adx_events = []
        dropped = 0
        while not self._queue.empty():
            (time_fired, event) = self._queue.get_nowait()
            adx_event, dropped = self._parse_event(time_fired, event, dropped)
            self._queue.task_done()
            if adx_event is not None:
                adx_events.append(adx_event)

        if dropped:
            _LOGGER.warning(
                "Dropped %d old events, consider filtering messages", dropped
            )

        if adx_events:
            event_string = "".join(adx_events)

            try:
                await self.menuai.async_add_executor_job(
                    self._client.ingest_data, event_string
                )

            except KustoServiceError as err:
                _LOGGER.error("Could not find database or table: %s", err)
            except KustoAuthenticationError as err:
                _LOGGER.error("Could not authenticate to Azure Data Explorer: %s", err)

        self._schedule_next_send()

    def _parse_event(
        self,
        time_fired: datetime,
        state: State,
        dropped: int,
    ) -> tuple[str | None, int]:
        """Parse event by checking if it needs to be sent, and format it."""

        if state.state in FILTER_STATES or not self._entities_filter(state.entity_id):
            return None, dropped
        if (utcnow() - time_fired).seconds > DEFAULT_MAX_DELAY + self._send_interval:
            return None, dropped + 1

        json_event = json.dumps(obj=state, cls=ExtendedJSONEncoder)

        return (json_event, dropped)
