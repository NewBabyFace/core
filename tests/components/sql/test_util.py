"""Test the sql utils."""

from menuai.components.recorder import Recorder, get_instance
from menuai.components.sql.util import resolve_db_url
from menuai.core import menuai


async def test_resolve_db_url_when_none_configured(
    recorder_mock: Recorder,
    menuai: menuai,
) -> None:
    """Test return recorder db_url if provided db_url is None."""
    db_url = None
    resolved_url = resolve_db_url(menuai, db_url)

    assert resolved_url == get_instance(menuai).db_url


async def test_resolve_db_url_when_configured(menuai: menuai) -> None:
    """Test return provided db_url if it's set."""
    db_url = "mssql://"
    resolved_url = resolve_db_url(menuai, db_url)

    assert resolved_url == db_url
