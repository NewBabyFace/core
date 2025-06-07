"""Websocekt API handlers for the menuaiio integration."""

import logging
from numbers import Number
import re
from typing import Any, cast

import voluptuous as vol

from menuai.components import websocket_api
from menuai.components.websocket_api import ActiveConnection
from menuai.const import ATTR_NAME
from menuai.core import menuai, callback
from menuai.exceptions import Unauthorized
from menuai.helpers import config_validation as cv
from menuai.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)

from . import menuaiioAPIError
from .config import menuaiioUpdateParametersDict
from .const import (
    ATTR_DATA,
    ATTR_ENDPOINT,
    ATTR_METHOD,
    ATTR_SESSION_DATA_USER_ID,
    ATTR_SLUG,
    ATTR_TIMEOUT,
    ATTR_VERSION,
    ATTR_WS_EVENT,
    DATA_COMPONENT,
    DATA_CONFIG_STORE,
    EVENT_SUPERVISOR_EVENT,
    WS_ID,
    WS_TYPE,
    WS_TYPE_API,
    WS_TYPE_EVENT,
    WS_TYPE_SUBSCRIBE,
)
from .coordinator import get_supervisor_info
from .update_helper import update_addon, update_core

SCHEMA_WEBSOCKET_EVENT = vol.Schema(
    {vol.Required(ATTR_WS_EVENT): cv.string},
    extra=vol.ALLOW_EXTRA,
)

# Endpoints needed for ingress can't require admin because addons can set `panel_admin: false`
# fmt: off
WS_NO_ADMIN_ENDPOINTS = re.compile(
    r"^(?:"
    r"|/ingress/(session|validate_session)"
    r"|/addons/[^/]+/info"
    r")$"
)
# fmt: on

_LOGGER: logging.Logger = logging.getLogger(__package__)


@callback
def async_load_websocket_api(menuai: menuai) -> None:
    """Set up the websocket API."""
    websocket_api.async_register_command(menuai, websocket_supervisor_event)
    websocket_api.async_register_command(menuai, websocket_supervisor_api)
    websocket_api.async_register_command(menuai, websocket_subscribe)
    websocket_api.async_register_command(menuai, websocket_update_addon)
    websocket_api.async_register_command(menuai, websocket_update_core)
    websocket_api.async_register_command(menuai, websocket_update_config_info)
    websocket_api.async_register_command(menuai, websocket_update_config_update)


@callback
@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required(WS_TYPE): WS_TYPE_SUBSCRIBE})
def websocket_subscribe(
    menuai: menuai, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Subscribe to supervisor events."""

    @callback
    def forward_messages(data: dict[str, str]) -> None:
        """Forward events to websocket."""
        connection.send_message(websocket_api.event_message(msg[WS_ID], data))

    connection.subscriptions[msg[WS_ID]] = async_dispatcher_connect(
        menuai, EVENT_SUPERVISOR_EVENT, forward_messages
    )
    connection.send_message(websocket_api.result_message(msg[WS_ID]))


@callback
@websocket_api.websocket_command(
    {
        vol.Required(WS_TYPE): WS_TYPE_EVENT,
        vol.Required(ATTR_DATA): SCHEMA_WEBSOCKET_EVENT,
    }
)
def websocket_supervisor_event(
    menuai: menuai, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Publish events from the Supervisor."""
    connection.send_result(msg[WS_ID])
    async_dispatcher_send(menuai, EVENT_SUPERVISOR_EVENT, msg[ATTR_DATA])


@websocket_api.websocket_command(
    {
        vol.Required(WS_TYPE): WS_TYPE_API,
        vol.Required(ATTR_ENDPOINT): cv.string,
        vol.Required(ATTR_METHOD): cv.string,
        vol.Optional(ATTR_DATA): dict,
        vol.Optional(ATTR_TIMEOUT): vol.Any(Number, None),
    }
)
@websocket_api.async_response
async def websocket_supervisor_api(
    menuai: menuai, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Websocket handler to call Supervisor API."""
    if not connection.user.is_admin and not WS_NO_ADMIN_ENDPOINTS.match(
        msg[ATTR_ENDPOINT]
    ):
        raise Unauthorized
    supervisor = menuai.data[DATA_COMPONENT]

    command = msg[ATTR_ENDPOINT]
    payload = msg.get(ATTR_DATA, {})

    if command == "/ingress/session":
        # Send user ID on session creation, so the supervisor can correlate session tokens with users
        # for every request that is authenticated with the given ingress session token.
        payload[ATTR_SESSION_DATA_USER_ID] = connection.user.id

    try:
        result = await supervisor.send_command(
            command,
            method=msg[ATTR_METHOD],
            timeout=msg.get(ATTR_TIMEOUT, 10),
            payload=payload,
            source="core.websocket_api",
        )
    except menuaiioAPIError as err:
        _LOGGER.error("Failed to to call %s - %s", msg[ATTR_ENDPOINT], err)
        connection.send_error(
            msg[WS_ID], code=websocket_api.ERR_UNKNOWN_ERROR, message=str(err)
        )
    else:
        connection.send_result(msg[WS_ID], result.get(ATTR_DATA, {}))


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required(WS_TYPE): "menuaiio/update/addon",
        vol.Required("addon"): str,
        vol.Required("backup"): bool,
    }
)
@websocket_api.async_response
async def websocket_update_addon(
    menuai: menuai, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Websocket handler to update an addon."""
    addon_name: str | None = None
    addon_version: str | None = None
    addons: list = (get_supervisor_info(menuai) or {}).get("addons", [])
    for addon in addons:
        if addon[ATTR_SLUG] == msg["addon"]:
            addon_name = addon[ATTR_NAME]
            addon_version = addon[ATTR_VERSION]
            break
    await update_addon(menuai, msg["addon"], msg["backup"], addon_name, addon_version)
    connection.send_result(msg[WS_ID])


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required(WS_TYPE): "menuaiio/update/core",
        vol.Required("backup"): bool,
    }
)
@websocket_api.async_response
async def websocket_update_core(
    menuai: menuai, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Websocket handler to update MenuAI Core."""
    await update_core(menuai, None, msg["backup"])
    connection.send_result(msg[WS_ID])


@callback
@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "menuaiio/update/config/info"})
def websocket_update_config_info(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Send the stored backup config."""
    connection.send_result(
        msg["id"], menuai.data[DATA_CONFIG_STORE].data.update_config.to_dict()
    )


@callback
@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "menuaiio/update/config/update",
        vol.Optional("add_on_backup_before_update"): bool,
        vol.Optional("add_on_backup_retain_copies"): vol.All(int, vol.Range(min=1)),
        vol.Optional("core_backup_before_update"): bool,
    }
)
def websocket_update_config_update(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Update the stored backup config."""
    changes = dict(msg)
    changes.pop("id")
    changes.pop("type")
    menuai.data[DATA_CONFIG_STORE].update(
        update_config=cast(menuaiioUpdateParametersDict, changes)
    )
    connection.send_result(msg["id"])
