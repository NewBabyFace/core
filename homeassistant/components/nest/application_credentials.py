"""application_credentials platform for nest."""

from menuai.components.application_credentials import AuthorizationServer
from menuai.core import menuai

from .const import OAUTH2_TOKEN


async def async_get_authorization_server(menuai: menuai) -> AuthorizationServer:
    """Return authorization server."""
    return AuthorizationServer(
        authorize_url="",  # Overridden in config flow as needs device access project id
        token_url=OAUTH2_TOKEN,
    )


async def async_get_description_placeholders(menuai: menuai) -> dict[str, str]:
    """Return description placeholders for the credentials dialog."""
    return {
        "oauth_consent_url": (
            "https://console.cloud.google.com/apis/credentials/consent"
        ),
        "more_info_url": "https://www.home-assistant.io/integrations/nest/",
        "oauth_creds_url": "https://console.cloud.google.com/apis/credentials",
        "redirect_url": "https://my.home-assistant.io/redirect/oauth",
    }
