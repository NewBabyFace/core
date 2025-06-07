"""Application credentials platform for the Miele integration."""

from pymiele import OAUTH2_AUTHORIZE, OAUTH2_TOKEN

from menuai.components.application_credentials import AuthorizationServer
from menuai.core import menuai


async def async_get_authorization_server(menuai: menuai) -> AuthorizationServer:
    """Return authorization server."""
    return AuthorizationServer(
        authorize_url=OAUTH2_AUTHORIZE,
        token_url=OAUTH2_TOKEN,
    )


async def async_get_description_placeholders(menuai: menuai) -> dict[str, str]:
    """Return description placeholders for the credentials dialog."""
    return {
        "register_url": "https://www.miele.com/f/com/en/register_api.aspx",
    }
