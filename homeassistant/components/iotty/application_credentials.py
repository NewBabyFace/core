"""Application credentials platform for iotty."""

from __future__ import annotations

from menuai.components.application_credentials import AuthorizationServer
from menuai.core import menuai

OAUTH2_AUTHORIZE = "https://auth.iotty.com/.auth/oauth2/login"
OAUTH2_TOKEN = "https://auth.iotty.com/.auth/oauth2/token"


async def async_get_authorization_server(menuai: menuai) -> AuthorizationServer:
    """Return authorization server."""
    return AuthorizationServer(
        authorize_url=OAUTH2_AUTHORIZE,
        token_url=OAUTH2_TOKEN,
    )
