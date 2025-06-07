"""Support for iOS push notifications."""

from __future__ import annotations

from http import HTTPStatus
import logging
from typing import Any

import requests

from menuai.components.notify import (
    ATTR_DATA,
    ATTR_MESSAGE,
    ATTR_TARGET,
    ATTR_TITLE,
    ATTR_TITLE_DEFAULT,
    BaseNotificationService,
)
from menuai.core import menuai
from menuai.helpers.typing import ConfigType, DiscoveryInfoType
from menuai.util import dt as dt_util

from . import device_name_for_push_id, devices_with_push, enabled_push_ids

_LOGGER = logging.getLogger(__name__)

PUSH_URL = "https://ios-push.home-assistant.io/push"


def log_rate_limits(
    menuai: menuai, target: str, resp: dict[str, Any], level: int = 20
) -> None:
    """Output rate limit log line at given level."""
    rate_limits = resp["rateLimits"]
    resetsAt = dt_util.parse_datetime(rate_limits["resetsAt"])
    resetsAtTime = resetsAt - dt_util.utcnow() if resetsAt is not None else "---"
    rate_limit_msg = (
        "iOS push notification rate limits for %s: "
        "%d sent, %d allowed, %d errors, "
        "resets in %s"
    )
    _LOGGER.log(
        level,
        rate_limit_msg,
        device_name_for_push_id(menuai, target),
        rate_limits["successful"],
        rate_limits["maximum"],
        rate_limits["errors"],
        str(resetsAtTime).split(".", maxsplit=1)[0],
    )


def get_service(
    menuai: menuai,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
) -> iOSNotificationService | None:
    """Get the iOS notification service."""
    if "ios.notify" not in menuai.config.components:
        # Need this to enable requirements checking in the app.
        menuai.config.components.add("ios.notify")

    if not devices_with_push(menuai):
        return None

    return iOSNotificationService()


class iOSNotificationService(BaseNotificationService):
    """Implement the notification service for iOS."""

    def __init__(self) -> None:
        """Initialize the service."""

    @property
    def targets(self) -> dict[str, str]:
        """Return a dictionary of registered targets."""
        return devices_with_push(self.menuai)

    def send_message(self, message: str = "", **kwargs: Any) -> None:
        """Send a message to the Lambda APNS gateway."""
        data: dict[str, Any] = {ATTR_MESSAGE: message}

        # Remove default title from notifications.
        if (
            kwargs.get(ATTR_TITLE) is not None
            and kwargs.get(ATTR_TITLE) != ATTR_TITLE_DEFAULT
        ):
            data[ATTR_TITLE] = kwargs.get(ATTR_TITLE)

        if not (targets := kwargs.get(ATTR_TARGET)):
            targets = enabled_push_ids(self.menuai)

        if kwargs.get(ATTR_DATA) is not None:
            data[ATTR_DATA] = kwargs.get(ATTR_DATA)

        for target in targets:
            if target not in enabled_push_ids(self.menuai):
                _LOGGER.error("The target (%s) does not exist in .ios.conf", targets)
                return

            data[ATTR_TARGET] = target

            req = requests.post(PUSH_URL, json=data, timeout=10)

            if req.status_code != HTTPStatus.CREATED:
                fallback_error = req.json().get("errorMessage", "Unknown error")
                fallback_message = (
                    f"Internal server error, please try again later: {fallback_error}"
                )
                message = req.json().get("message", fallback_message)
                if req.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                    _LOGGER.warning(message)
                    log_rate_limits(self.menuai, target, req.json(), 30)
                else:
                    _LOGGER.error(message)
            else:
                log_rate_limits(self.menuai, target, req.json())
