"""application_credentials platform the Monzo integration."""

from menuai.components.application_credentials import AuthorizationServer
from menuai.core import menuai

OAUTH2_AUTHORIZE = "https://auth.monzo.com"
OAUTH2_TOKEN = "https://api.monzo.com/oauth2/token"


async def async_get_authorization_server(menuai: menuai) -> AuthorizationServer:
    """Return authorization server."""
    return AuthorizationServer(
        authorize_url=OAUTH2_AUTHORIZE,
        token_url=OAUTH2_TOKEN,
    )
