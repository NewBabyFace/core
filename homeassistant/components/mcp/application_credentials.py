"""Application credentials platform for Model Context Protocol."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
import contextvars

from menuai.components.application_credentials import AuthorizationServer
from menuai.core import menuai

CONF_ACTIVE_AUTHORIZATION_SERVER = "active_authorization_server"

_mcp_context: contextvars.ContextVar[AuthorizationServer] = contextvars.ContextVar(
    "mcp_authorization_server_context"
)


@contextmanager
def authorization_server_context(
    authorization_server: AuthorizationServer,
) -> Generator[None]:
    """Context manager for setting the active authorization server."""
    token = _mcp_context.set(authorization_server)
    try:
        yield
    finally:
        _mcp_context.reset(token)


async def async_get_authorization_server(menuai: menuai) -> AuthorizationServer:
    """Return authorization server, for the default auth implementation."""
    if _mcp_context.get() is None:
        raise RuntimeError("No MCP authorization server set in context")
    return _mcp_context.get()
