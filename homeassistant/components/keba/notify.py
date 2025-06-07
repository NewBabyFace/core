"""Support for Keba notifications."""

from __future__ import annotations

from menuai.components.notify import ATTR_DATA, BaseNotificationService
from menuai.core import menuai
from menuai.helpers.typing import ConfigType, DiscoveryInfoType

from . import DOMAIN


async def async_get_service(
    menuai: menuai,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
) -> KebaNotificationService:
    """Return the notify service."""

    client = menuai.data[DOMAIN]
    return KebaNotificationService(client)


class KebaNotificationService(BaseNotificationService):
    """Notification service for KEBA EV Chargers."""

    def __init__(self, client):
        """Initialize the service."""
        self._client = client

    async def async_send_message(self, message="", **kwargs):
        """Send the message."""
        text = message.replace(" ", "$")  # Will be translated back by the display

        data = kwargs[ATTR_DATA] or {}
        min_time = float(data.get("min_time", 2))
        max_time = float(data.get("max_time", 10))

        await self._client.set_text(text, min_time, max_time)
