"""API for yolink bound to MenuAI OAuth."""

from aiohttp import ClientSession
from yolink.auth_mgr import YoLinkAuthMgr

from menuai.core import menuai
from menuai.helpers import config_entry_oauth2_flow


class ConfigEntryAuth(YoLinkAuthMgr):
    """Provide yolink authentication tied to an OAuth2 based config entry."""

    def __init__(
        self,
        menuai: menuai,
        websession: ClientSession,
        oauth2Session: config_entry_oauth2_flow.OAuth2Session,
    ) -> None:
        """Initialize yolink Auth."""
        self.menuai = menuai
        self.oauth_session = oauth2Session
        super().__init__(websession)

    def access_token(self) -> str:
        """Return the access token."""
        return self.oauth_session.token["access_token"]

    async def check_and_refresh_token(self) -> str:
        """Check the token."""
        await self.oauth_session.async_ensure_token_valid()
        return self.access_token()
