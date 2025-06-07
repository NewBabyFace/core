"""Support for displaying persistent notifications."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from enum import StrEnum
from functools import partial
import logging
from typing import Any, Final, TypedDict

import voluptuous as vol

from menuai.components import websocket_api
from menuai.core import CALLBACK_TYPE, menuai, ServiceCall, callback
from menuai.helpers import config_validation as cv, singleton
from menuai.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from menuai.helpers.typing import ConfigType
from menuai.loader import bind_menuai
from menuai.util import dt as dt_util
from menuai.util.signal_type import SignalType
from menuai.util.uuid import random_uuid_hex

DOMAIN = "persistent_notification"

ATTR_CREATED_AT: Final = "created_at"
ATTR_MESSAGE: Final = "message"
ATTR_NOTIFICATION_ID: Final = "notification_id"
ATTR_TITLE: Final = "title"
ATTR_STATUS: Final = "status"


class Notification(TypedDict):
    """Persistent notification."""

    created_at: datetime
    message: str
    notification_id: str
    title: str | None


class UpdateType(StrEnum):
    """Persistent notification update type."""

    CURRENT = "current"
    ADDED = "added"
    REMOVED = "removed"
    UPDATED = "updated"


SIGNAL_PERSISTENT_NOTIFICATIONS_UPDATED = SignalType[
    UpdateType, dict[str, Notification]
]("persistent_notifications_updated")

SCHEMA_SERVICE_NOTIFICATION = vol.Schema(
    {vol.Required(ATTR_NOTIFICATION_ID): cv.string}
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


@callback
def async_register_callback(
    menuai: menuai,
    _callback: Callable[[UpdateType, dict[str, Notification]], None],
) -> CALLBACK_TYPE:
    """Register a callback."""
    return async_dispatcher_connect(
        menuai, SIGNAL_PERSISTENT_NOTIFICATIONS_UPDATED, _callback
    )


@bind_menuai
def create(
    menuai: menuai,
    message: str,
    title: str | None = None,
    notification_id: str | None = None,
) -> None:
    """Generate a notification."""
    menuai.add_job(async_create, menuai, message, title, notification_id)


@bind_menuai
def dismiss(menuai: menuai, notification_id: str) -> None:
    """Remove a notification."""
    menuai.add_job(async_dismiss, menuai, notification_id)


@callback
@bind_menuai
def async_create(
    menuai: menuai,
    message: str,
    title: str | None = None,
    notification_id: str | None = None,
) -> None:
    """Generate a notification."""
    notifications = _async_get_or_create_notifications(menuai)
    if notification_id is None:
        notification_id = random_uuid_hex()
    notifications[notification_id] = {
        ATTR_MESSAGE: message,
        ATTR_NOTIFICATION_ID: notification_id,
        ATTR_TITLE: title,
        ATTR_CREATED_AT: dt_util.utcnow(),
    }

    async_dispatcher_send(
        menuai,
        SIGNAL_PERSISTENT_NOTIFICATIONS_UPDATED,
        UpdateType.ADDED,
        {notification_id: notifications[notification_id]},
    )


@callback
@singleton.singleton(DOMAIN)
def _async_get_or_create_notifications(menuai: menuai) -> dict[str, Notification]:
    """Get or create notifications data."""
    return {}


@callback
@bind_menuai
def async_dismiss(menuai: menuai, notification_id: str) -> None:
    """Remove a notification."""
    notifications = _async_get_or_create_notifications(menuai)
    if not (notification := notifications.pop(notification_id, None)):
        return
    async_dispatcher_send(
        menuai,
        SIGNAL_PERSISTENT_NOTIFICATIONS_UPDATED,
        UpdateType.REMOVED,
        {notification_id: notification},
    )


@callback
def async_dismiss_all(menuai: menuai) -> None:
    """Remove all notifications."""
    notifications = _async_get_or_create_notifications(menuai)
    notifications_copy = notifications.copy()
    notifications.clear()
    async_dispatcher_send(
        menuai,
        SIGNAL_PERSISTENT_NOTIFICATIONS_UPDATED,
        UpdateType.REMOVED,
        notifications_copy,
    )


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the persistent notification component."""

    @callback
    def create_service(call: ServiceCall) -> None:
        """Handle a create notification service call."""
        async_create(
            menuai,
            call.data[ATTR_MESSAGE],
            call.data.get(ATTR_TITLE),
            call.data.get(ATTR_NOTIFICATION_ID),
        )

    @callback
    def dismiss_service(call: ServiceCall) -> None:
        """Handle the dismiss notification service call."""
        async_dismiss(menuai, call.data[ATTR_NOTIFICATION_ID])

    @callback
    def dismiss_all_service(call: ServiceCall) -> None:
        """Handle the dismiss all notification service call."""
        async_dismiss_all(menuai)

    menuai.services.async_register(
        DOMAIN,
        "create",
        create_service,
        vol.Schema(
            {
                vol.Required(ATTR_MESSAGE): cv.string,
                vol.Optional(ATTR_TITLE): cv.string,
                vol.Optional(ATTR_NOTIFICATION_ID): cv.string,
            }
        ),
    )

    menuai.services.async_register(
        DOMAIN, "dismiss", dismiss_service, SCHEMA_SERVICE_NOTIFICATION
    )

    menuai.services.async_register(DOMAIN, "dismiss_all", dismiss_all_service, None)

    websocket_api.async_register_command(menuai, websocket_get_notifications)
    websocket_api.async_register_command(menuai, websocket_subscribe_notifications)

    return True


@callback
@websocket_api.websocket_command({vol.Required("type"): "persistent_notification/get"})
def websocket_get_notifications(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: Mapping[str, Any],
) -> None:
    """Return a list of persistent_notifications."""
    connection.send_message(
        websocket_api.result_message(
            msg["id"], list(_async_get_or_create_notifications(menuai).values())
        )
    )


@callback
def _async_send_notification_update(
    connection: websocket_api.ActiveConnection,
    msg_id: int,
    update_type: UpdateType,
    notifications: dict[str, Notification],
) -> None:
    """Send persistent_notification update."""
    connection.send_message(
        websocket_api.event_message(
            msg_id, {"type": update_type, "notifications": notifications}
        )
    )


@callback
@websocket_api.websocket_command(
    {vol.Required("type"): "persistent_notification/subscribe"}
)
def websocket_subscribe_notifications(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: Mapping[str, Any],
) -> None:
    """Return a list of persistent_notifications."""
    notifications = _async_get_or_create_notifications(menuai)
    msg_id = msg["id"]
    notify_func = partial(_async_send_notification_update, connection, msg_id)
    connection.subscriptions[msg_id] = async_dispatcher_connect(
        menuai, SIGNAL_PERSISTENT_NOTIFICATIONS_UPDATED, notify_func
    )
    connection.send_result(msg_id)
    notify_func(UpdateType.CURRENT, notifications)
