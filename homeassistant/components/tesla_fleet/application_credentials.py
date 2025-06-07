"""Application Credentials platform the Tesla Fleet integration."""

from menuai.components.application_credentials import ClientCredential
from menuai.core import menuai
from menuai.helpers import config_entry_oauth2_flow

from .oauth import TeslaUserImplementation


async def async_get_auth_implementation(
    menuai: menuai, auth_domain: str, credential: ClientCredential
) -> config_entry_oauth2_flow.AbstractOAuth2Implementation:
    """Return auth implementation."""
    return TeslaUserImplementation(
        menuai,
        auth_domain,
        credential,
    )
