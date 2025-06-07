"""application_credentials platform for Geocaching."""

from menuai.components.application_credentials import ClientCredential
from menuai.core import menuai
from menuai.helpers import config_entry_oauth2_flow

from .oauth import GeocachingOAuth2Implementation


async def async_get_auth_implementation(
    menuai: menuai, auth_domain: str, credential: ClientCredential
) -> config_entry_oauth2_flow.AbstractOAuth2Implementation:
    """Return auth implementation."""
    return GeocachingOAuth2Implementation(menuai, auth_domain, credential)
