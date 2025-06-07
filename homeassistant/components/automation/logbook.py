"""Describe logbook events."""

from collections.abc import Callable
from typing import Any

from menuai.components.logbook import (
    LOGBOOK_ENTRY_CONTEXT_ID,
    LOGBOOK_ENTRY_ENTITY_ID,
    LOGBOOK_ENTRY_MESSAGE,
    LOGBOOK_ENTRY_NAME,
    LOGBOOK_ENTRY_SOURCE,
    LazyEventPartialState,
)
from menuai.const import ATTR_ENTITY_ID, ATTR_NAME
from menuai.core import menuai, callback

from . import ATTR_SOURCE, EVENT_AUTOMATION_TRIGGERED
from .const import DOMAIN


@callback
def async_describe_events(
    menuai: menuai,
    async_describe_event: Callable[
        [str, str, Callable[[LazyEventPartialState], dict[str, Any]]], None
    ],
) -> None:
    """Describe logbook events."""

    @callback
    def async_describe_logbook_event(event: LazyEventPartialState) -> dict[str, Any]:
        """Describe a logbook event."""
        data = event.data
        message = "triggered"
        if ATTR_SOURCE in data:
            message = f"{message} by {data[ATTR_SOURCE]}"

        return {
            LOGBOOK_ENTRY_NAME: data.get(ATTR_NAME),
            LOGBOOK_ENTRY_MESSAGE: message,
            LOGBOOK_ENTRY_SOURCE: data.get(ATTR_SOURCE),
            LOGBOOK_ENTRY_ENTITY_ID: data.get(ATTR_ENTITY_ID),
            LOGBOOK_ENTRY_CONTEXT_ID: event.context_id,
        }

    async_describe_event(
        DOMAIN, EVENT_AUTOMATION_TRIGGERED, async_describe_logbook_event
    )
