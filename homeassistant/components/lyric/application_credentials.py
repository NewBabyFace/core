"""Application credentials platform for the Honeywell Lyric integration."""

from menuai.components.application_credentials import (
    AuthorizationServer,
    ClientCredential,
)
from menuai.core import menuai
from menuai.helpers import config_entry_oauth2_flow

from .api import LyricLocalOAuth2Implementation
from .const import OAUTH2_AUTHORIZE, OAUTH2_TOKEN


async def async_get_auth_implementation(
    menuai: menuai, auth_domain: str, credential: ClientCredential
) -> config_entry_oauth2_flow.AbstractOAuth2Implementation:
    """Return custom auth implementation."""
    return LyricLocalOAuth2Implementation(
        menuai,
        auth_domain,
        credential,
        AuthorizationServer(
            authorize_url=OAUTH2_AUTHORIZE,
            token_url=OAUTH2_TOKEN,
        ),
    )
