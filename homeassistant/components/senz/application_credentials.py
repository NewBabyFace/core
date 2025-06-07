"""Application credentials platform for senz."""

from aiosenz import AUTHORIZATION_ENDPOINT, TOKEN_ENDPOINT

from menuai.components.application_credentials import AuthorizationServer
from menuai.core import menuai


async def async_get_authorization_server(menuai: menuai) -> AuthorizationServer:
    """Return authorization server."""
    return AuthorizationServer(
        authorize_url=AUTHORIZATION_ENDPOINT,
        token_url=TOKEN_ENDPOINT,
    )
