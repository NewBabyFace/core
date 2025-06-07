"""Helpers for MenuAI dispatcher & internal component/platform."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Coroutine
from functools import partial
import logging
from typing import Any, overload

from menuai.core import (
    menuaiJob,
    menuaiJobType,
    menuai,
    callback,
    get_menuaijob_callable_job_type,
)
from menuai.loader import bind_menuai
from menuai.util.async_ import run_callback_threadsafe
from menuai.util.logging import catch_log_exception, log_exception

# Explicit reexport of 'SignalType' for backwards compatibility
from menuai.util.signal_type import SignalType as SignalType  # noqa: PLC0414

_LOGGER = logging.getLogger(__name__)
DATA_DISPATCHER = "dispatcher"


type _DispatcherDataType[*_Ts] = dict[
    SignalType[*_Ts] | str,
    dict[
        Callable[[*_Ts], Any] | Callable[..., Any],
        menuaiJob[..., None | Coroutine[Any, Any, None]] | None,
    ],
]


@overload
@bind_menuai
def dispatcher_connect[*_Ts](
    menuai: menuai, signal: SignalType[*_Ts], target: Callable[[*_Ts], None]
) -> Callable[[], None]: ...


@overload
@bind_menuai
def dispatcher_connect(
    menuai: menuai, signal: str, target: Callable[..., None]
) -> Callable[[], None]: ...


@bind_menuai  # type: ignore[misc]  # workaround; exclude typing of 2 overload in func def
def dispatcher_connect[*_Ts](
    menuai: menuai,
    signal: SignalType[*_Ts],
    target: Callable[[*_Ts], None],
) -> Callable[[], None]:
    """Connect a callable function to a signal."""
    async_unsub = run_callback_threadsafe(
        menuai.loop, async_dispatcher_connect, menuai, signal, target
    ).result()

    def remove_dispatcher() -> None:
        """Remove signal listener."""
        run_callback_threadsafe(menuai.loop, async_unsub).result()

    return remove_dispatcher


@callback
def _async_remove_dispatcher[*_Ts](
    dispatchers: _DispatcherDataType[*_Ts],
    signal: SignalType[*_Ts] | str,
    target: Callable[[*_Ts], Any] | Callable[..., Any],
) -> None:
    """Remove signal listener."""
    try:
        signal_dispatchers = dispatchers[signal]
        del signal_dispatchers[target]
        # Cleanup the signal dict if it is now empty
        # to prevent memory leaks
        if not signal_dispatchers:
            del dispatchers[signal]
    except (KeyError, ValueError):
        # KeyError is key target listener did not exist
        # ValueError if listener did not exist within signal
        _LOGGER.warning("Unable to remove unknown dispatcher %s", target)


@overload
@callback
@bind_menuai
def async_dispatcher_connect[*_Ts](
    menuai: menuai, signal: SignalType[*_Ts], target: Callable[[*_Ts], Any]
) -> Callable[[], None]: ...


@overload
@callback
@bind_menuai
def async_dispatcher_connect(
    menuai: menuai, signal: str, target: Callable[..., Any]
) -> Callable[[], None]: ...


@callback
@bind_menuai
def async_dispatcher_connect[*_Ts](
    menuai: menuai,
    signal: SignalType[*_Ts] | str,
    target: Callable[[*_Ts], Any] | Callable[..., Any],
) -> Callable[[], None]:
    """Connect a callable function to a signal.

    This method must be run in the event loop.
    """
    if DATA_DISPATCHER not in menuai.data:
        menuai.data[DATA_DISPATCHER] = defaultdict(dict)
    dispatchers: _DispatcherDataType[*_Ts] = menuai.data[DATA_DISPATCHER]
    dispatchers[signal][target] = None
    # Use a partial for the remove since it uses
    # less memory than a full closure since a partial copies
    # the body of the function and we don't have to store
    # many different copies of the same function
    return partial(_async_remove_dispatcher, dispatchers, signal, target)


@overload
@bind_menuai
def dispatcher_send[*_Ts](
    menuai: menuai, signal: SignalType[*_Ts], *args: *_Ts
) -> None: ...


@overload
@bind_menuai
def dispatcher_send(menuai: menuai, signal: str, *args: Any) -> None: ...


@bind_menuai  # type: ignore[misc]  # workaround; exclude typing of 2 overload in func def
def dispatcher_send[*_Ts](
    menuai: menuai, signal: SignalType[*_Ts], *args: *_Ts
) -> None:
    """Send signal and data."""
    menuai.loop.call_soon_threadsafe(async_dispatcher_send_internal, menuai, signal, *args)


def _format_err[*_Ts](
    signal: SignalType[*_Ts] | str,
    target: Callable[[*_Ts], Any] | Callable[..., Any],
    *args: Any,
) -> str:
    """Format error message."""

    return (
        # Functions wrapped in partial do not have a __name__
        f"Exception in {getattr(target, '__name__', None) or target} "
        f"when dispatching '{signal}': {args}"
    )


def _generate_job[*_Ts](
    signal: SignalType[*_Ts] | str, target: Callable[[*_Ts], Any] | Callable[..., Any]
) -> menuaiJob[..., Coroutine[Any, Any, None] | None]:
    """Generate a menuaiJob for a signal and target."""
    job_type = get_menuaijob_callable_job_type(target)
    name = f"dispatcher {signal}"
    if job_type is menuaiJobType.Callback:
        # We will catch exceptions in the callback to avoid
        # wrapping the callback since calling wraps() is more
        # expensive than the whole dispatcher_send process
        return menuaiJob(target, name, job_type=job_type)
    return menuaiJob(
        catch_log_exception(
            target, partial(_format_err, signal, target), job_type=job_type
        ),
        name,
        job_type=job_type,
    )


@overload
@callback
@bind_menuai
def async_dispatcher_send[*_Ts](
    menuai: menuai, signal: SignalType[*_Ts], *args: *_Ts
) -> None: ...


@overload
@callback
@bind_menuai
def async_dispatcher_send(menuai: menuai, signal: str, *args: Any) -> None: ...


@callback
@bind_menuai
def async_dispatcher_send[*_Ts](
    menuai: menuai, signal: SignalType[*_Ts] | str, *args: *_Ts
) -> None:
    """Send signal and data.

    This method must be run in the event loop.
    """
    # We turned on asyncio debug in April 2024 in the dev containers
    # in the hope of catching some of the issues that have been
    # reported. It will take a while to get all the issues fixed in
    # custom components.
    #
    # In 2025.5 we should guard the `verify_event_loop_thread`
    # check with a check for the `menuai.config.debug` flag being set as
    # long term we don't want to be checking this in production
    # environments since it is a performance hit.
    menuai.verify_event_loop_thread("async_dispatcher_send")
    async_dispatcher_send_internal(menuai, signal, *args)


@callback
@bind_menuai
def async_dispatcher_send_internal[*_Ts](
    menuai: menuai, signal: SignalType[*_Ts] | str, *args: *_Ts
) -> None:
    """Send signal and data.

    This method is intended to only be used by core internally
    and should not be considered a stable API. We will make
    breaking changes to this function in the future and it
    should not be used in integrations.

    This method must be run in the event loop.
    """
    if (maybe_dispatchers := menuai.data.get(DATA_DISPATCHER)) is None:
        return
    dispatchers: _DispatcherDataType[*_Ts] = maybe_dispatchers
    if (target_list := dispatchers.get(signal)) is None:
        return

    for target, job in list(target_list.items()):
        if job is None:
            job = _generate_job(signal, target)
            target_list[target] = job
        # We do not wrap Callback jobs in catch_log_exception since
        # single use dispatchers spend more time wrapping the callback
        # than the actual callback takes to run in many cases.
        if job.job_type is menuaiJobType.Callback:
            try:
                job.target(*args)
            except Exception:  # noqa: BLE001
                log_exception(partial(_format_err, signal, target), *args)  # type: ignore[arg-type]
        else:
            menuai.async_run_menuai_job(job, *args)
