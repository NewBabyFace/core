"""Support for SMS notifications from the Dovado router."""

from __future__ import annotations

import logging

from menuai.components.notify import ATTR_TARGET, BaseNotificationService
from menuai.core import menuai
from menuai.helpers.typing import ConfigType, DiscoveryInfoType

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


def get_service(
    menuai: menuai,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
) -> DovadoSMSNotificationService:
    """Get the Dovado Router SMS notification service."""
    return DovadoSMSNotificationService(menuai.data[DOMAIN].client)


class DovadoSMSNotificationService(BaseNotificationService):
    """Implement the notification service for the Dovado SMS component."""

    def __init__(self, client):
        """Initialize the service."""
        self._client = client

    def send_message(self, message, **kwargs):
        """Send SMS to the specified target phone number."""
        if not (target := kwargs.get(ATTR_TARGET)):
            _LOGGER.error("One target is required")
            return

        self._client.send_sms(target, message)
