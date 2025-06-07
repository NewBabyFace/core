"""application_credentials platform the yale integration."""

from menuai.components.application_credentials import AuthorizationServer
from menuai.core import menuai

OAUTH2_AUTHORIZE = "https://oauth.aaecosystem.com/authorize"
OAUTH2_TOKEN = "https://oauth.aaecosystem.com/access_token"


async def async_get_authorization_server(menuai: menuai) -> AuthorizationServer:
    """Return authorization server."""
    return AuthorizationServer(
        authorize_url=OAUTH2_AUTHORIZE,
        token_url=OAUTH2_TOKEN,
    )
