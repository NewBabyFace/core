"""Utils for Vodafone Station."""

from aiohttp import ClientSession, CookieJar

from menuai.core import menuai
from menuai.helpers import aiohttp_client


async def async_client_session(menuai: menuai) -> ClientSession:
    """Return a new aiohttp session."""
    return aiohttp_client.async_create_clientsession(
        menuai, verify_ssl=False, cookie_jar=CookieJar(unsafe=True)
    )
