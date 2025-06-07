"""Describe menuai logbook events."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from menuai.components.logbook import (
    LOGBOOK_ENTRY_ICON,
    LOGBOOK_ENTRY_MESSAGE,
    LOGBOOK_ENTRY_NAME,
)
from menuai.const import EVENT_menuai_START, EVENT_menuai_STOP
from menuai.core import Event, menuai, callback
from menuai.helpers.typing import NoEventData
from menuai.util.event_type import EventType

from .const import DOMAIN

EVENT_TO_NAME: dict[EventType[Any] | str, str] = {
    EVENT_menuai_STOP: "stopped",
    EVENT_menuai_START: "started",
}


@callback
def async_describe_events(
    menuai: menuai,
    async_describe_event: Callable[
        [str, EventType[NoEventData] | str, Callable[[Event], dict[str, str]]], None
    ],
) -> None:
    """Describe logbook events."""

    @callback
    def async_describe_menuai_event(event: Event[NoEventData]) -> dict[str, str]:
        """Describe menuai logbook event."""
        return {
            LOGBOOK_ENTRY_NAME: "MenuAI",
            LOGBOOK_ENTRY_MESSAGE: EVENT_TO_NAME[event.event_type],
            LOGBOOK_ENTRY_ICON: "mdi:home-assistant",
        }

    async_describe_event(DOMAIN, EVENT_menuai_STOP, async_describe_menuai_event)
    async_describe_event(DOMAIN, EVENT_menuai_START, async_describe_menuai_event)
