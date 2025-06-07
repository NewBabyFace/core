"""application_credentials platform for nest."""

import oauth2client

from menuai.components.application_credentials import (
    AuthorizationServer,
    ClientCredential,
)
from menuai.core import menuai
from menuai.helpers import config_entry_oauth2_flow

from .api import GoogleHybridAuth

AUTHORIZATION_SERVER = AuthorizationServer(
    oauth2client.GOOGLE_AUTH_URI, oauth2client.GOOGLE_TOKEN_URI
)


async def async_get_auth_implementation(
    menuai: menuai, auth_domain: str, credential: ClientCredential
) -> config_entry_oauth2_flow.AbstractOAuth2Implementation:
    """Return auth implementation."""
    return GoogleHybridAuth(menuai, auth_domain, credential, AUTHORIZATION_SERVER)


async def async_get_description_placeholders(menuai: menuai) -> dict[str, str]:
    """Return description placeholders for the credentials dialog."""
    return {
        "oauth_consent_url": (
            "https://console.cloud.google.com/apis/credentials/consent"
        ),
        "more_info_url": "https://www.home-assistant.io/integrations/google/",
        "oauth_creds_url": "https://console.cloud.google.com/apis/credentials",
    }
