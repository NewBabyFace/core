"""Define notion utilities."""

from aionotion import (
    async_get_client_with_credentials as cwc,
    async_get_client_with_refresh_token as cwrt,
)
from aionotion.client import Client

from menuai.core import menuai
from menuai.helpers import aiohttp_client
from menuai.helpers.instance_id import async_get


async def async_get_client_with_credentials(
    menuai: menuai, email: str, password: str
) -> Client:
    """Get a Notion client with credentials."""
    session = aiohttp_client.async_get_clientsession(menuai)
    instance_id = await async_get(menuai)
    return await cwc(email, password, session=session, session_name=instance_id)


async def async_get_client_with_refresh_token(
    menuai: menuai, user_uuid: str, refresh_token: str
) -> Client:
    """Get a Notion client with credentials."""
    session = aiohttp_client.async_get_clientsession(menuai)
    instance_id = await async_get(menuai)
    return await cwrt(
        user_uuid, refresh_token, session=session, session_name=instance_id
    )
