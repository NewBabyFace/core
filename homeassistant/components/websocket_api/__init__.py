"""WebSocket based API for MenuAI."""

from __future__ import annotations

from typing import Final, cast

from menuai.core import menuai, callback
from menuai.helpers import config_validation as cv
from menuai.helpers.typing import ConfigType, VolSchemaType
from menuai.loader import bind_menuai

from . import commands, connection, const, decorators, http, messages  # noqa: F401
from .connection import ActiveConnection, current_connection  # noqa: F401
from .const import (  # noqa: F401
    ERR_HOME_ASSISTANT_ERROR,
    ERR_INVALID_FORMAT,
    ERR_NOT_ALLOWED,
    ERR_NOT_FOUND,
    ERR_NOT_SUPPORTED,
    ERR_SERVICE_VALIDATION_ERROR,
    ERR_TEMPLATE_ERROR,
    ERR_TIMEOUT,
    ERR_UNAUTHORIZED,
    ERR_UNKNOWN_COMMAND,
    ERR_UNKNOWN_ERROR,
    TYPE_RESULT,
    AsyncWebSocketCommandHandler,
    WebSocketCommandHandler,
)
from .decorators import (  # noqa: F401
    async_response,
    require_admin,
    websocket_command,
    ws_require_user,
)
from .messages import (  # noqa: F401
    BASE_COMMAND_MESSAGE_SCHEMA,
    error_message,
    event_message,
    result_message,
)

DOMAIN: Final = const.DOMAIN

DEPENDENCIES: Final[tuple[str]] = ("http",)

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


@bind_menuai
@callback
def async_register_command(
    menuai: menuai,
    command_or_handler: str | const.WebSocketCommandHandler,
    handler: const.WebSocketCommandHandler | None = None,
    schema: VolSchemaType | None = None,
) -> None:
    """Register a websocket command."""
    if handler is None:
        handler = cast(const.WebSocketCommandHandler, command_or_handler)
        command = handler._ws_command  # type: ignore[attr-defined]  # noqa: SLF001
        schema = handler._ws_schema  # type: ignore[attr-defined]  # noqa: SLF001
    else:
        command = command_or_handler
    if (handlers := menuai.data.get(DOMAIN)) is None:
        handlers = menuai.data[DOMAIN] = {}
    handlers[command] = (handler, schema)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Initialize the websocket API."""
    menuai.http.register_view(http.WebsocketAPIView())
    commands.async_register_commands(menuai, async_register_command)
    return True
