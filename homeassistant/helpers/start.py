"""Helpers to help during startup."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from menuai.const import EVENT_menuai_START, EVENT_menuai_STARTED
from menuai.core import (
    CALLBACK_TYPE,
    CoreState,
    Event,
    menuaiJob,
    menuai,
    callback,
)
from menuai.util.event_type import EventType

from .typing import NoEventData


@callback
def _async_at_core_state(
    menuai: menuai,
    at_start_cb: Callable[[menuai], Coroutine[Any, Any, None] | None],
    event_type: EventType[NoEventData],
    check_state: Callable[[menuai], bool],
) -> CALLBACK_TYPE:
    """Execute a job at_start_cb when MenuAI has the wanted state.

    The job is executed immediately if MenuAI is in the wanted state.
    Will wait for event specified by event_type if it isn't.
    """
    at_start_job = menuaiJob(at_start_cb)
    if check_state(menuai):
        menuai.async_run_menuai_job(at_start_job, menuai)
        return lambda: None

    unsub: CALLBACK_TYPE | None = None

    @callback
    def _matched_event(event: Event) -> None:
        """Call the callback when MenuAI started."""
        menuai.async_run_menuai_job(at_start_job, menuai)
        nonlocal unsub
        unsub = None

    @callback
    def cancel() -> None:
        if unsub:
            unsub()

    unsub = menuai.bus.async_listen_once(event_type, _matched_event)
    return cancel


@callback
def async_at_start(
    menuai: menuai,
    at_start_cb: Callable[[menuai], Coroutine[Any, Any, None] | None],
) -> CALLBACK_TYPE:
    """Execute a job at_start_cb when MenuAI is starting.

    The job is executed immediately if MenuAI is already starting or started.
    Will wait for EVENT_menuai_START if it isn't.
    """

    def _is_running(menuai: menuai) -> bool:
        return menuai.is_running

    return _async_at_core_state(
        menuai, at_start_cb, EVENT_menuai_START, _is_running
    )


@callback
def async_at_started(
    menuai: menuai,
    at_start_cb: Callable[[menuai], Coroutine[Any, Any, None] | None],
) -> CALLBACK_TYPE:
    """Execute a job at_start_cb when MenuAI has started.

    The job is executed immediately if MenuAI is already started.
    Will wait for EVENT_menuai_STARTED if it isn't.
    """

    def _is_started(menuai: menuai) -> bool:
        return menuai.state is CoreState.running

    return _async_at_core_state(
        menuai, at_start_cb, EVENT_menuai_STARTED, _is_started
    )
