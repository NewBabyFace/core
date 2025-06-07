"""Application credentials platform for spotify."""

from menuai.components.application_credentials import AuthorizationServer
from menuai.core import menuai


async def async_get_authorization_server(menuai: menuai) -> AuthorizationServer:
    """Return authorization server."""
    return AuthorizationServer(
        authorize_url="https://accounts.spotify.com/authorize",
        token_url="https://accounts.spotify.com/api/token",
    )
