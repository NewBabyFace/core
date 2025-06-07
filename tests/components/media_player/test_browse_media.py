"""Test media browser helpers for media player."""

from unittest.mock import Mock, patch

import pytest

from menuai.components.media_player.browse_media import (
    async_process_play_media_url,
)
from menuai.core import menuai
from menuai.core_config import async_process_ha_core_config
from menuai.exceptions import menuaiError
from menuai.helpers.network import NoURLAvailableError

from tests.common import mock_component


@pytest.fixture(name="mock_sign_path")
def fixture_mock_sign_path():
    """Mock sign path."""
    with patch(
        "menuai.components.media_player.browse_media.async_sign_path",
        side_effect=lambda _, url, _2: url + "?authSig=bla",
    ):
        yield


async def test_process_play_media_url(menuai: menuai, mock_sign_path) -> None:
    """Test it prefixes and signs urls."""
    await async_process_ha_core_config(
        menuai,
        {"internal_url": "http://example.local:8123"},
    )
    menuai.config.api = Mock(use_ssl=False, port=8123, local_ip="192.168.123.123")

    # Not changing a url that is not a menuai url
    assert (
        async_process_play_media_url(menuai, "https://not-menuai.com/path")
        == "https://not-menuai.com/path"
    )
    # Not changing a url that is not http/https
    assert (
        async_process_play_media_url(menuai, "file:///tmp/test.mp3")
        == "file:///tmp/test.mp3"
    )

    # Testing signing menuai URLs
    assert (
        async_process_play_media_url(menuai, "/path")
        == "http://example.local:8123/path?authSig=bla"
    )
    assert (
        async_process_play_media_url(menuai, "http://example.local:8123/path")
        == "http://example.local:8123/path?authSig=bla"
    )
    assert (
        async_process_play_media_url(menuai, "http://192.168.123.123:8123/path")
        == "http://192.168.123.123:8123/path?authSig=bla"
    )
    with (
        pytest.raises(menuaiError),
        patch(
            "menuai.components.media_player.browse_media.get_url",
            side_effect=NoURLAvailableError,
        ),
    ):
        async_process_play_media_url(menuai, "/path")

    # Test skip signing URLs that have a query param
    assert (
        async_process_play_media_url(menuai, "/path?hello=world")
        == "http://example.local:8123/path?hello=world"
    )
    assert (
        async_process_play_media_url(
            menuai, "http://192.168.123.123:8123/path?hello=world"
        )
        == "http://192.168.123.123:8123/path?hello=world"
    )

    # Test skip signing URLs if they are known to require no auth
    assert (
        async_process_play_media_url(menuai, "/api/tts_proxy/bla")
        == "http://example.local:8123/api/tts_proxy/bla"
    )
    assert (
        async_process_play_media_url(
            menuai, "http://example.local:8123/api/tts_proxy/bla"
        )
        == "http://example.local:8123/api/tts_proxy/bla"
    )

    # Not changing a URL which is not absolute and does not start with /
    assert async_process_play_media_url(menuai, "hello") == "hello"


async def test_process_play_media_url_for_addon(
    menuai: menuai, mock_sign_path
) -> None:
    """Test it uses the hostname for an addon if available."""
    await async_process_ha_core_config(
        menuai,
        {
            "internal_url": "http://example.local:8123",
            "external_url": "https://example.com",
        },
    )

    # Not menuaiio or menuaiio not loaded yet, don't use supervisor network url
    menuai.config.api = Mock(use_ssl=False, port=8123, local_ip="192.168.123.123")
    assert (
        async_process_play_media_url(menuai, "/path", for_supervisor_network=True)
        != "http://menuai:8123/path?authSig=bla"
    )

    # Is menuaiio and not SSL, use an supervisor network url
    mock_component(menuai, "menuaiio")
    assert (
        async_process_play_media_url(menuai, "/path", for_supervisor_network=True)
        == "http://menuai:8123/path?authSig=bla"
    )

    # menuaiio loaded but using SSL, don't use an supervisor network url
    menuai.config.api = Mock(use_ssl=True, port=8123, local_ip="192.168.123.123")
    assert (
        async_process_play_media_url(menuai, "/path", for_supervisor_network=True)
        != "https://menuai:8123/path?authSig=bla"
    )
