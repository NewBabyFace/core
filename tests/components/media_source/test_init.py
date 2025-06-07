"""Test Media Source initialization."""

from unittest.mock import Mock, patch

import pytest
import yarl

from menuai.components import media_source
from menuai.components.media_player import BrowseError, MediaClass
from menuai.components.media_source import const, models
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.typing import WebSocketGenerator


async def test_is_media_source_id() -> None:
    """Test media source validation."""
    assert media_source.is_media_source_id(media_source.URI_SCHEME)
    assert media_source.is_media_source_id(f"{media_source.URI_SCHEME}domain")
    assert media_source.is_media_source_id(
        f"{media_source.URI_SCHEME}domain/identifier"
    )
    assert not media_source.is_media_source_id("test")


async def test_generate_media_source_id() -> None:
    """Test identifier generation."""
    tests = [
        (None, None),
        (None, ""),
        ("", ""),
        ("domain", None),
        ("domain", ""),
        ("domain", "identifier"),
    ]

    for domain, identifier in tests:
        assert media_source.is_media_source_id(
            media_source.generate_media_source_id(domain, identifier)
        )


async def test_async_browse_media(menuai: menuai) -> None:
    """Test browse media."""
    assert await async_setup_component(menuai, media_source.DOMAIN, {})
    await menuai.async_block_till_done()

    # Test non-media ignored (/media has test.mp3 and not_media.txt)
    media = await media_source.async_browse_media(menuai, "")
    assert isinstance(media, media_source.models.BrowseMediaSource)
    assert media.title == "media"
    assert len(media.children) == 2

    # Test content filter
    media = await media_source.async_browse_media(
        menuai,
        "",
        content_filter=lambda item: item.media_content_type.startswith("video/"),
    )
    assert isinstance(media, media_source.models.BrowseMediaSource)
    assert media.title == "media"
    assert len(media.children) == 1, media.children
    media.children[0].title = "Epic Sax Guy 10 Hours"
    assert media.not_shown == 1

    # Test content filter adds to original not_shown
    orig_browse = models.MediaSourceItem.async_browse

    async def not_shown_browse(self):
        """Patch browsed item to set not_shown base value."""
        item = await orig_browse(self)
        item.not_shown = 10
        return item

    with patch(
        "menuai.components.media_source.models.MediaSourceItem.async_browse",
        not_shown_browse,
    ):
        media = await media_source.async_browse_media(
            menuai,
            "",
            content_filter=lambda item: item.media_content_type.startswith("video/"),
        )
    assert isinstance(media, media_source.models.BrowseMediaSource)
    assert media.title == "media"
    assert len(media.children) == 1, media.children
    media.children[0].title = "Epic Sax Guy 10 Hours"
    assert media.not_shown == 11

    # Test invalid media content
    with pytest.raises(BrowseError):
        await media_source.async_browse_media(menuai, "invalid")

    # Test base URI returns all domains
    media = await media_source.async_browse_media(menuai, const.URI_SCHEME)
    assert isinstance(media, media_source.models.BrowseMediaSource)
    assert len(media.children) == 1
    assert media.children[0].title == "My media"


async def test_async_resolve_media(menuai: menuai) -> None:
    """Test browse media."""
    assert await async_setup_component(menuai, media_source.DOMAIN, {})
    await menuai.async_block_till_done()

    media = await media_source.async_resolve_media(
        menuai,
        media_source.generate_media_source_id(media_source.DOMAIN, "local/test.mp3"),
        None,
    )
    assert isinstance(media, media_source.models.PlayMedia)
    assert media.url == "/media/local/test.mp3"
    assert media.mime_type == "audio/mpeg"


async def test_async_resolve_media_no_entity(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test browse media."""
    assert await async_setup_component(menuai, media_source.DOMAIN, {})
    await menuai.async_block_till_done()

    with pytest.raises(RuntimeError):
        await media_source.async_resolve_media(
            menuai,
            media_source.generate_media_source_id(
                media_source.DOMAIN, "local/test.mp3"
            ),
        )


async def test_async_unresolve_media(menuai: menuai) -> None:
    """Test browse media."""
    assert await async_setup_component(menuai, media_source.DOMAIN, {})
    await menuai.async_block_till_done()

    # Test no media content
    with pytest.raises(media_source.Unresolvable):
        await media_source.async_resolve_media(menuai, "", None)

    # Test invalid media content
    with pytest.raises(media_source.Unresolvable):
        await media_source.async_resolve_media(menuai, "invalid", None)

    # Test invalid media source
    with pytest.raises(media_source.Unresolvable):
        await media_source.async_resolve_media(
            menuai, "media-source://media_source2", None
        )


async def test_websocket_browse_media(
    menuai: menuai, menuai_ws_client: WebSocketGenerator
) -> None:
    """Test browse media websocket."""
    assert await async_setup_component(menuai, media_source.DOMAIN, {})
    await menuai.async_block_till_done()

    client = await menuai_ws_client(menuai)

    media = media_source.models.BrowseMediaSource(
        domain=media_source.DOMAIN,
        identifier="/media",
        title="Local Media",
        media_class=MediaClass.DIRECTORY,
        media_content_type="listing",
        can_play=False,
        can_expand=True,
    )

    with patch(
        "menuai.components.media_source.async_browse_media",
        return_value=media,
    ):
        await client.send_json(
            {
                "id": 1,
                "type": "media_source/browse_media",
            }
        )

        msg = await client.receive_json()

    assert msg["success"]
    assert msg["id"] == 1
    assert media.as_dict() == msg["result"]

    with patch(
        "menuai.components.media_source.async_browse_media",
        side_effect=BrowseError("test"),
    ):
        await client.send_json(
            {
                "id": 2,
                "type": "media_source/browse_media",
                "media_content_id": "invalid",
            }
        )

        msg = await client.receive_json()

    assert not msg["success"]
    assert msg["error"]["code"] == "browse_media_failed"
    assert msg["error"]["message"] == "test"


@pytest.mark.parametrize("filename", ["test.mp3", "Epic Sax Guy 10 Hours.mp4"])
async def test_websocket_resolve_media(
    menuai: menuai, menuai_ws_client: WebSocketGenerator, filename
) -> None:
    """Test browse media websocket."""
    assert await async_setup_component(menuai, media_source.DOMAIN, {})
    await menuai.async_block_till_done()

    client = await menuai_ws_client(menuai)

    media = media_source.models.PlayMedia(
        f"/media/local/{filename}",
        "audio/mpeg",
    )

    with patch(
        "menuai.components.media_source.async_resolve_media",
        return_value=media,
    ):
        await client.send_json(
            {
                "id": 1,
                "type": "media_source/resolve_media",
                "media_content_id": f"{const.URI_SCHEME}{media_source.DOMAIN}/local/{filename}",
            }
        )

        msg = await client.receive_json()

    assert msg["success"]
    assert msg["id"] == 1
    assert msg["result"]["mime_type"] == media.mime_type

    # Validate url is relative and signed.
    assert msg["result"]["url"][0] == "/"
    parsed = yarl.URL(msg["result"]["url"])
    assert parsed.path == media.url
    assert "authSig" in parsed.query

    with patch(
        "menuai.components.media_source.async_resolve_media",
        side_effect=media_source.Unresolvable("test"),
    ):
        await client.send_json(
            {
                "id": 2,
                "type": "media_source/resolve_media",
                "media_content_id": "invalid",
            }
        )

        msg = await client.receive_json()

    assert not msg["success"]
    assert msg["error"]["code"] == "resolve_media_failed"
    assert msg["error"]["message"] == "test"


async def test_browse_resolve_without_setup() -> None:
    """Test browse and resolve work without being setup."""
    with pytest.raises(BrowseError):
        await media_source.async_browse_media(Mock(data={}), None)

    with pytest.raises(media_source.Unresolvable):
        await media_source.async_resolve_media(Mock(data={}), None, None)
