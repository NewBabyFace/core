"""Application credentials platform for Husqvarna Automower."""

from menuai.components.application_credentials import AuthorizationServer
from menuai.core import menuai

from .const import OAUTH2_AUTHORIZE, OAUTH2_TOKEN


async def async_get_authorization_server(menuai: menuai) -> AuthorizationServer:
    """Return authorization server."""
    return AuthorizationServer(
        authorize_url=OAUTH2_AUTHORIZE,
        token_url=OAUTH2_TOKEN,
    )
