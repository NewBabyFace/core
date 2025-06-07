"""Blebox helpers tests."""

from aiohttp.helpers import BasicAuth

from menuai.components.blebox.helpers import get_maybe_authenticated_session
from menuai.core import menuai


async def test_get_maybe_authenticated_session_none(menuai: menuai) -> None:
    """Tests if session auth is None."""
    session = get_maybe_authenticated_session(menuai=menuai, username="", password="")
    assert session.auth is None


async def test_get_maybe_authenticated_session_auth(menuai: menuai) -> None:
    """Tests if session have BasicAuth."""
    session = get_maybe_authenticated_session(
        menuai=menuai, username="user", password="password"
    )
    assert isinstance(session.auth, BasicAuth)
