"""Websocket commands for the Backup integration."""

from typing import Any

import voluptuous as vol

from menuai.components import websocket_api
from menuai.core import menuai, callback
from menuai.helpers.backup import async_subscribe_events

from .const import DATA_MANAGER
from .manager import ManagerStateEvent


@callback
def async_register_websocket_handlers(menuai: menuai) -> None:
    """Register websocket commands."""
    websocket_api.async_register_command(menuai, handle_subscribe_events)


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "backup/subscribe_events"})
@websocket_api.async_response
async def handle_subscribe_events(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Subscribe to backup events."""

    def on_event(event: ManagerStateEvent) -> None:
        connection.send_message(websocket_api.event_message(msg["id"], event))

    if DATA_MANAGER in menuai.data:
        manager = menuai.data[DATA_MANAGER]
        on_event(manager.last_event)
    connection.subscriptions[msg["id"]] = async_subscribe_events(menuai, on_event)
    connection.send_result(msg["id"])
