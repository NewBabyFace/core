"""Mycroft AI notification platform."""

from __future__ import annotations

import logging

from mycroftapi import MycroftAPI

from menuai.components.notify import BaseNotificationService
from menuai.core import menuai
from menuai.helpers.typing import ConfigType, DiscoveryInfoType

_LOGGER = logging.getLogger(__name__)


def get_service(
    menuai: menuai,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
) -> MycroftNotificationService:
    """Get the Mycroft notification service."""
    return MycroftNotificationService(menuai.data["mycroft"])


class MycroftNotificationService(BaseNotificationService):
    """The Mycroft Notification Service."""

    def __init__(self, mycroft_ip):
        """Initialize the service."""
        self.mycroft_ip = mycroft_ip

    def send_message(self, message="", **kwargs):
        """Send a message mycroft to speak on instance."""

        text = message
        mycroft = MycroftAPI(self.mycroft_ip)
        if mycroft is not None:
            mycroft.speak_text(text)
        else:
            _LOGGER.log("Could not reach this instance of mycroft")
