"""Collection of helper methods.

All containing methods are legacy helpers that should not be used by new
components. Instead call the service directly.
"""

from typing import Any

from menuai.components.notify import (
    ATTR_DATA,
    ATTR_MESSAGE,
    ATTR_TITLE,
    DOMAIN,
    SERVICE_NOTIFY,
)
from menuai.core import menuai
from menuai.loader import bind_menuai


@bind_menuai
def send_message(
    menuai: menuai, message: str, title: str | None = None, data: Any = None
) -> None:
    """Send a notification message."""
    info = {ATTR_MESSAGE: message}

    if title is not None:
        info[ATTR_TITLE] = title

    if data is not None:
        info[ATTR_DATA] = data

    menuai.services.call(DOMAIN, SERVICE_NOTIFY, info)
