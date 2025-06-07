"""Application credentials platform for LaMetric."""

from menuai.components.application_credentials import AuthorizationServer
from menuai.core import menuai


async def async_get_authorization_server(menuai: menuai) -> AuthorizationServer:
    """Return authorization server."""
    return AuthorizationServer(
        authorize_url="https://developer.lametric.com/api/v2/oauth2/authorize",
        token_url="https://developer.lametric.com/api/v2/oauth2/token",
    )
