"""Blebox helpers."""

from __future__ import annotations

import aiohttp

from menuai.core import menuai
from menuai.helpers.aiohttp_client import (
    async_create_clientsession,
    async_get_clientsession,
)


def get_maybe_authenticated_session(
    menuai: menuai, password: str | None, username: str | None
) -> aiohttp.ClientSession:
    """Return proper session object."""
    if username and password:
        auth = aiohttp.BasicAuth(login=username, password=password)
        return async_create_clientsession(menuai, auth=auth)

    return async_get_clientsession(menuai)
