"""API for YouTube bound to MenuAI OAuth."""

from youtubeaio.types import AuthScope
from youtubeaio.youtube import YouTube

from menuai.const import CONF_ACCESS_TOKEN
from menuai.core import menuai
from menuai.helpers import config_entry_oauth2_flow
from menuai.helpers.aiohttp_client import async_get_clientsession


class AsyncConfigEntryAuth:
    """Provide Google authentication tied to an OAuth2 based config entry."""

    youtube: YouTube | None = None

    def __init__(
        self,
        menuai: menuai,
        oauth2_session: config_entry_oauth2_flow.OAuth2Session,
    ) -> None:
        """Initialize YouTube Auth."""
        self.oauth_session = oauth2_session
        self.menuai = menuai

    @property
    def access_token(self) -> str:
        """Return the access token."""
        return self.oauth_session.token[CONF_ACCESS_TOKEN]  # type: ignore[no-any-return]

    async def check_and_refresh_token(self) -> str:
        """Check the token."""
        await self.oauth_session.async_ensure_token_valid()
        return self.access_token

    async def get_resource(self) -> YouTube:
        """Create resource."""
        token = await self.check_and_refresh_token()
        if self.youtube is None:
            self.youtube = YouTube(session=async_get_clientsession(self.menuai))
        await self.youtube.set_user_authentication(token, [AuthScope.READ_ONLY])
        return self.youtube
