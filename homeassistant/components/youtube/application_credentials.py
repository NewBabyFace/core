"""application_credentials platform for YouTube."""

from menuai.components.application_credentials import AuthorizationServer
from menuai.core import menuai


async def async_get_authorization_server(menuai: menuai) -> AuthorizationServer:
    """Return authorization server."""
    return AuthorizationServer(
        "https://accounts.google.com/o/oauth2/v2/auth",
        "https://oauth2.googleapis.com/token",
    )
