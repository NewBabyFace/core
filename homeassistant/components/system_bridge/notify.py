"""Support for System Bridge notification service."""

from __future__ import annotations

import logging
from typing import Any

from systembridgemodels.notification import Notification

from menuai.components.notify import (
    ATTR_DATA,
    ATTR_TITLE,
    ATTR_TITLE_DEFAULT,
    BaseNotificationService,
)
from menuai.const import ATTR_ICON, CONF_ENTITY_ID
from menuai.core import menuai
from menuai.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN
from .coordinator import SystemBridgeDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

ATTR_ACTIONS = "actions"
ATTR_AUDIO = "audio"
ATTR_IMAGE = "image"
ATTR_TIMEOUT = "timeout"


async def async_get_service(
    menuai: menuai,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
) -> SystemBridgeNotificationService | None:
    """Get the System Bridge notification service."""
    if discovery_info is None:
        return None

    coordinator: SystemBridgeDataUpdateCoordinator = menuai.data[DOMAIN][
        discovery_info[CONF_ENTITY_ID]
    ]

    return SystemBridgeNotificationService(coordinator)


class SystemBridgeNotificationService(BaseNotificationService):
    """Implement the notification service for System Bridge."""

    def __init__(
        self,
        coordinator: SystemBridgeDataUpdateCoordinator,
    ) -> None:
        """Initialize the service."""
        self._coordinator: SystemBridgeDataUpdateCoordinator = coordinator

    async def async_send_message(
        self,
        message: str = "",
        **kwargs: Any,
    ) -> None:
        """Send a message."""
        data = kwargs.get(ATTR_DATA, {}) or {}

        notification = Notification(
            actions=data.get(ATTR_ACTIONS),
            audio=data.get(ATTR_AUDIO),
            icon=data.get(ATTR_ICON),
            image=data.get(ATTR_IMAGE),
            message=message,
            timeout=data.get(ATTR_TIMEOUT),
            title=kwargs.get(ATTR_TITLE, data.get(ATTR_TITLE, ATTR_TITLE_DEFAULT)),
        )

        _LOGGER.debug("Sending notification: %s", notification)

        await self._coordinator.websocket_client.send_notification(notification)
