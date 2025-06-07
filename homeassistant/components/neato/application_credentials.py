"""Application credentials platform for neato."""

from pybotvac import Neato

from menuai.components.application_credentials import (
    AuthorizationServer,
    ClientCredential,
)
from menuai.core import menuai
from menuai.helpers import config_entry_oauth2_flow

from . import api


async def async_get_auth_implementation(
    menuai: menuai, auth_domain: str, credential: ClientCredential
) -> config_entry_oauth2_flow.AbstractOAuth2Implementation:
    """Return auth implementation for a custom auth implementation."""
    vendor = Neato()
    return api.NeatoImplementation(
        menuai,
        auth_domain,
        credential,
        AuthorizationServer(
            authorize_url=vendor.auth_endpoint,
            token_url=vendor.token_endpoint,
        ),
    )
