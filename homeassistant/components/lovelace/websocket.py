"""Websocket API for Lovelace."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import TYPE_CHECKING, Any

import voluptuous as vol

from menuai.components import websocket_api
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import config_validation as cv
from menuai.helpers.json import json_fragment

from .const import CONF_URL_PATH, LOVELACE_DATA, ConfigNotFound
from .dashboard import LovelaceConfig

if TYPE_CHECKING:
    from .resources import ResourceStorageCollection

type AsyncLovelaceWebSocketCommandHandler[_R] = Callable[
    [menuai, websocket_api.ActiveConnection, dict[str, Any], LovelaceConfig],
    Awaitable[_R],
]


def _handle_errors[_R](
    func: AsyncLovelaceWebSocketCommandHandler[_R],
) -> websocket_api.AsyncWebSocketCommandHandler:
    """Handle error with WebSocket calls."""

    @wraps(func)
    async def send_with_error_handling(
        menuai: menuai,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        url_path = msg.get(CONF_URL_PATH)
        config = menuai.data[LOVELACE_DATA].dashboards.get(url_path)

        if config is None:
            connection.send_error(
                msg["id"], "config_not_found", f"Unknown config specified: {url_path}"
            )
            return

        error = None
        try:
            result = await func(menuai, connection, msg, config)
        except ConfigNotFound:
            error = "config_not_found", "No config found."
        except menuaiError as err:
            error = "error", str(err)

        if error is not None:
            connection.send_error(msg["id"], *error)
            return

        connection.send_result(msg["id"], result)

    return send_with_error_handling


@websocket_api.async_response
async def websocket_lovelace_resources(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Send Lovelace UI resources over WebSocket connection.

    This function is used in YAML mode.
    """
    await websocket_lovelace_resources_impl(menuai, connection, msg)


async def websocket_lovelace_resources_impl(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Help send Lovelace UI resources over WebSocket connection.

    This function is called by both Storage and YAML mode WS handlers.
    """
    resources = menuai.data[LOVELACE_DATA].resources
    if TYPE_CHECKING:
        assert isinstance(resources, ResourceStorageCollection)

    if menuai.config.safe_mode:
        connection.send_result(msg["id"], [])
        return

    if not resources.loaded:
        await resources.async_load()
        resources.loaded = True

    connection.send_result(msg["id"], resources.async_items())


@websocket_api.websocket_command(
    {
        "type": "lovelace/config",
        vol.Optional("force", default=False): bool,
        vol.Optional(CONF_URL_PATH): vol.Any(None, cv.string),
    }
)
@websocket_api.async_response
@_handle_errors
async def websocket_lovelace_config(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    config: LovelaceConfig,
) -> json_fragment:
    """Send Lovelace UI config over WebSocket connection."""
    return await config.async_json(msg["force"])


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        "type": "lovelace/config/save",
        "config": vol.Any(str, dict),
        vol.Optional(CONF_URL_PATH): vol.Any(None, cv.string),
    }
)
@websocket_api.async_response
@_handle_errors
async def websocket_lovelace_save_config(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    config: LovelaceConfig,
) -> None:
    """Save Lovelace UI configuration."""
    await config.async_save(msg["config"])


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        "type": "lovelace/config/delete",
        vol.Optional(CONF_URL_PATH): vol.Any(None, cv.string),
    }
)
@websocket_api.async_response
@_handle_errors
async def websocket_lovelace_delete_config(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    config: LovelaceConfig,
) -> None:
    """Delete Lovelace UI configuration."""
    await config.async_delete()
