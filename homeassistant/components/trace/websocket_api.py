"""Websocket API for automation."""

import json
from typing import Any

import voluptuous as vol

from menuai.components import websocket_api
from menuai.core import menuai, callback
from menuai.exceptions import menuaiError
from menuai.helpers.dispatcher import (
    DATA_DISPATCHER,
    async_dispatcher_connect,
    async_dispatcher_send,
)
from menuai.helpers.json import ExtendedJSONEncoder
from menuai.helpers.script import (
    SCRIPT_BREAKPOINT_HIT,
    SCRIPT_DEBUG_CONTINUE_ALL,
    breakpoint_clear,
    breakpoint_clear_all,
    breakpoint_list,
    breakpoint_set,
    debug_continue,
    debug_step,
    debug_stop,
)

from .util import async_get_trace, async_list_contexts, async_list_traces

TRACE_DOMAINS = ("automation", "script")


@callback
def async_setup(menuai: menuai) -> None:
    """Set up the websocket API."""
    websocket_api.async_register_command(menuai, websocket_trace_get)
    websocket_api.async_register_command(menuai, websocket_trace_list)
    websocket_api.async_register_command(menuai, websocket_trace_contexts)
    websocket_api.async_register_command(menuai, websocket_breakpoint_clear)
    websocket_api.async_register_command(menuai, websocket_breakpoint_list)
    websocket_api.async_register_command(menuai, websocket_breakpoint_set)
    websocket_api.async_register_command(menuai, websocket_debug_continue)
    websocket_api.async_register_command(menuai, websocket_debug_step)
    websocket_api.async_register_command(menuai, websocket_debug_stop)
    websocket_api.async_register_command(menuai, websocket_subscribe_breakpoint_events)


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "trace/get",
        vol.Required("domain"): vol.In(TRACE_DOMAINS),
        vol.Required("item_id"): str,
        vol.Required("run_id"): str,
    }
)
@websocket_api.async_response
async def websocket_trace_get(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get a script or automation trace."""
    key = f"{msg['domain']}.{msg['item_id']}"
    run_id = msg["run_id"]

    try:
        requested_trace = await async_get_trace(menuai, key, run_id)
    except KeyError:
        connection.send_error(
            msg["id"], websocket_api.ERR_NOT_FOUND, "The trace could not be found"
        )
        return

    message = websocket_api.messages.result_message(msg["id"], requested_trace)

    connection.send_message(
        json.dumps(message, cls=ExtendedJSONEncoder, allow_nan=False)
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "trace/list",
        vol.Required("domain", "id"): vol.In(TRACE_DOMAINS),
        vol.Optional("item_id", "id"): str,
    }
)
@websocket_api.async_response
async def websocket_trace_list(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Summarize script and automation traces."""
    wanted_domain = msg["domain"]
    key = f"{msg['domain']}.{msg['item_id']}" if "item_id" in msg else None

    traces = await async_list_traces(menuai, wanted_domain, key)

    connection.send_result(msg["id"], traces)


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "trace/contexts",
        vol.Inclusive("domain", "id"): vol.In(TRACE_DOMAINS),
        vol.Inclusive("item_id", "id"): str,
    }
)
@websocket_api.async_response
async def websocket_trace_contexts(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Retrieve contexts we have traces for."""
    key = f"{msg['domain']}.{msg['item_id']}" if "item_id" in msg else None

    contexts = await async_list_contexts(menuai, key)

    connection.send_result(msg["id"], contexts)


@callback
@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "trace/debug/breakpoint/set",
        vol.Required("domain"): vol.In(TRACE_DOMAINS),
        vol.Required("item_id"): str,
        vol.Required("node"): str,
        vol.Optional("run_id"): str,
    }
)
def websocket_breakpoint_set(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Set breakpoint."""
    key = f"{msg['domain']}.{msg['item_id']}"
    node: str = msg["node"]
    run_id: str | None = msg.get("run_id")

    if (
        SCRIPT_BREAKPOINT_HIT not in menuai.data.get(DATA_DISPATCHER, {})
        or not menuai.data[DATA_DISPATCHER][SCRIPT_BREAKPOINT_HIT]
    ):
        raise menuaiError("No breakpoint subscription")

    result = breakpoint_set(menuai, key, run_id, node)
    connection.send_result(msg["id"], result)


@callback
@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "trace/debug/breakpoint/clear",
        vol.Required("domain"): vol.In(TRACE_DOMAINS),
        vol.Required("item_id"): str,
        vol.Required("node"): str,
        vol.Optional("run_id"): str,
    }
)
def websocket_breakpoint_clear(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Clear breakpoint."""
    key = f"{msg['domain']}.{msg['item_id']}"
    node: str = msg["node"]
    run_id: str | None = msg.get("run_id")

    result = breakpoint_clear(menuai, key, run_id, node)

    connection.send_result(msg["id"], result)


@callback
@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "trace/debug/breakpoint/list"})
def websocket_breakpoint_list(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """List breakpoints."""
    breakpoints = breakpoint_list(menuai)
    for _breakpoint in breakpoints:
        key = _breakpoint.pop("key")
        _breakpoint["domain"], _breakpoint["item_id"] = key.split(".", 1)

    connection.send_result(msg["id"], breakpoints)


@callback
@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): "trace/debug/breakpoint/subscribe"}
)
def websocket_subscribe_breakpoint_events(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Subscribe to breakpoint events."""

    @callback
    def breakpoint_hit(key: str, run_id: str, node: str) -> None:
        """Forward events to websocket."""
        domain, item_id = key.split(".", 1)
        connection.send_message(
            websocket_api.event_message(
                msg["id"],
                {
                    "domain": domain,
                    "item_id": item_id,
                    "run_id": run_id,
                    "node": node,
                },
            )
        )

    remove_signal = async_dispatcher_connect(
        menuai, SCRIPT_BREAKPOINT_HIT, breakpoint_hit
    )

    @callback
    def unsub() -> None:
        """Unsubscribe from breakpoint events."""
        remove_signal()
        if (
            SCRIPT_BREAKPOINT_HIT not in menuai.data.get(DATA_DISPATCHER, {})
            or not menuai.data[DATA_DISPATCHER][SCRIPT_BREAKPOINT_HIT]
        ):
            breakpoint_clear_all(menuai)
            async_dispatcher_send(menuai, SCRIPT_DEBUG_CONTINUE_ALL)

    connection.subscriptions[msg["id"]] = unsub

    connection.send_message(websocket_api.result_message(msg["id"]))


@callback
@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "trace/debug/continue",
        vol.Required("domain"): vol.In(TRACE_DOMAINS),
        vol.Required("item_id"): str,
        vol.Required("run_id"): str,
    }
)
def websocket_debug_continue(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Resume execution of halted script or automation."""
    key = f"{msg['domain']}.{msg['item_id']}"
    run_id: str = msg["run_id"]

    result = debug_continue(menuai, key, run_id)

    connection.send_result(msg["id"], result)


@callback
@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "trace/debug/step",
        vol.Required("domain"): vol.In(TRACE_DOMAINS),
        vol.Required("item_id"): str,
        vol.Required("run_id"): str,
    }
)
def websocket_debug_step(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Single step a halted script or automation."""
    key = f"{msg['domain']}.{msg['item_id']}"
    run_id: str = msg["run_id"]

    result = debug_step(menuai, key, run_id)

    connection.send_result(msg["id"], result)


@callback
@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "trace/debug/stop",
        vol.Required("domain"): vol.In(TRACE_DOMAINS),
        vol.Required("item_id"): str,
        vol.Required("run_id"): str,
    }
)
def websocket_debug_stop(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Stop a halted script or automation."""
    key = f"{msg['domain']}.{msg['item_id']}"
    run_id: str = msg["run_id"]

    result = debug_stop(menuai, key, run_id)

    connection.send_result(msg["id"], result)
