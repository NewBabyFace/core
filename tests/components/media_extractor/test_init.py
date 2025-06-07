"""The tests for Media Extractor integration."""

import os
import os.path
from typing import Any
from unittest.mock import patch

import pytest
from syrupy.assertion import SnapshotAssertion
from yt_dlp import DownloadError

from menuai.components.media_extractor.const import (
    ATTR_URL,
    DOMAIN,
    SERVICE_EXTRACT_MEDIA_URL,
)
from menuai.components.media_player import SERVICE_PLAY_MEDIA
from menuai.core import menuai, ServiceCall
from menuai.exceptions import menuaiError
from menuai.setup import async_setup_component

from . import YOUTUBE_EMPTY_PLAYLIST, YOUTUBE_PLAYLIST, YOUTUBE_VIDEO, MockYoutubeDL
from .const import NO_FORMATS_RESPONSE, SOUNDCLOUD_TRACK

from tests.common import MockConfigEntry, async_load_json_object_fixture


async def test_play_media_service_is_registered(menuai: menuai) -> None:
    """Test play media service is registered."""
    mock_config_entry = MockConfigEntry(domain=DOMAIN)

    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert menuai.services.has_service(DOMAIN, SERVICE_PLAY_MEDIA)
    assert menuai.services.has_service(DOMAIN, SERVICE_EXTRACT_MEDIA_URL)
    assert len(menuai.config_entries.async_entries(DOMAIN))


@pytest.mark.parametrize(
    "url",
    [
        YOUTUBE_VIDEO,
        SOUNDCLOUD_TRACK,
        NO_FORMATS_RESPONSE,
        YOUTUBE_PLAYLIST,
    ],
)
async def test_extract_media_service(
    menuai: menuai,
    mock_youtube_dl: MockYoutubeDL,
    snapshot: SnapshotAssertion,
    empty_media_extractor_config: dict[str, Any],
    url: str,
) -> None:
    """Test play media service is registered."""
    await async_setup_component(menuai, DOMAIN, empty_media_extractor_config)
    await menuai.async_block_till_done()

    assert (
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_EXTRACT_MEDIA_URL,
            {ATTR_URL: url},
            blocking=True,
            return_response=True,
        )
        == snapshot
    )


async def test_extracting_playlist_no_entries(
    menuai: menuai,
    mock_youtube_dl: MockYoutubeDL,
    empty_media_extractor_config: dict[str, Any],
) -> None:
    """Test extracting a playlist without entries."""

    await async_setup_component(menuai, DOMAIN, empty_media_extractor_config)
    await menuai.async_block_till_done()
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_EXTRACT_MEDIA_URL,
            {ATTR_URL: YOUTUBE_EMPTY_PLAYLIST},
            blocking=True,
            return_response=True,
        )


@pytest.mark.parametrize(
    "config_fixture", ["empty_media_extractor_config", "audio_media_extractor_config"]
)
@pytest.mark.parametrize(
    ("media_content_id", "media_content_type"),
    [
        (YOUTUBE_VIDEO, "VIDEO"),
        (SOUNDCLOUD_TRACK, "AUDIO"),
        (NO_FORMATS_RESPONSE, "AUDIO"),
    ],
)
async def test_play_media_service(
    menuai: menuai,
    mock_youtube_dl: MockYoutubeDL,
    service_calls: list[ServiceCall],
    snapshot: SnapshotAssertion,
    request: pytest.FixtureRequest,
    config_fixture: str,
    media_content_id: str,
    media_content_type: str,
) -> None:
    """Test play media service is registered."""
    config: dict[str, Any] = request.getfixturevalue(config_fixture)
    await async_setup_component(menuai, DOMAIN, config)
    await menuai.async_block_till_done()

    await menuai.services.async_call(
        DOMAIN,
        SERVICE_PLAY_MEDIA,
        {
            "entity_id": "media_player.bedroom",
            "media_content_type": media_content_type,
            "media_content_id": media_content_id,
        },
    )
    await menuai.async_block_till_done()

    assert len(service_calls) == 2
    assert service_calls[1].data == snapshot


async def test_download_error(
    menuai: menuai,
    empty_media_extractor_config: dict[str, Any],
    service_calls: list[ServiceCall],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test handling DownloadError."""

    with patch(
        "menuai.components.media_extractor.YoutubeDL.extract_info",
        side_effect=DownloadError("Message"),
    ):
        await async_setup_component(menuai, DOMAIN, empty_media_extractor_config)
        await menuai.async_block_till_done()

        await menuai.services.async_call(
            DOMAIN,
            SERVICE_PLAY_MEDIA,
            {
                "entity_id": "media_player.bedroom",
                "media_content_type": "VIDEO",
                "media_content_id": YOUTUBE_VIDEO,
            },
        )
        await menuai.async_block_till_done()

    assert len(service_calls) == 1
    assert f"Could not retrieve data for the URL: {YOUTUBE_VIDEO}" in caplog.text


async def test_no_target_entity(
    menuai: menuai,
    mock_youtube_dl: MockYoutubeDL,
    empty_media_extractor_config: dict[str, Any],
    service_calls: list[ServiceCall],
    snapshot: SnapshotAssertion,
) -> None:
    """Test having no target entity."""

    await async_setup_component(menuai, DOMAIN, empty_media_extractor_config)
    await menuai.async_block_till_done()

    await menuai.services.async_call(
        DOMAIN,
        SERVICE_PLAY_MEDIA,
        {
            "device_id": "fb034c3a9fefe47c584c32a6b51817eb",
            "media_content_type": "VIDEO",
            "media_content_id": YOUTUBE_VIDEO,
        },
    )
    await menuai.async_block_till_done()

    assert len(service_calls) == 2
    assert service_calls[1].data == snapshot


async def test_playlist(
    menuai: menuai,
    mock_youtube_dl: MockYoutubeDL,
    empty_media_extractor_config: dict[str, Any],
    service_calls: list[ServiceCall],
    snapshot: SnapshotAssertion,
) -> None:
    """Test extracting a playlist."""

    await async_setup_component(menuai, DOMAIN, empty_media_extractor_config)
    await menuai.async_block_till_done()

    await menuai.services.async_call(
        DOMAIN,
        SERVICE_PLAY_MEDIA,
        {
            "entity_id": "media_player.bedroom",
            "media_content_type": "VIDEO",
            "media_content_id": YOUTUBE_PLAYLIST,
        },
    )
    await menuai.async_block_till_done()

    assert len(service_calls) == 2
    assert service_calls[1].data == snapshot


async def test_playlist_no_entries(
    menuai: menuai,
    mock_youtube_dl: MockYoutubeDL,
    empty_media_extractor_config: dict[str, Any],
    service_calls: list[ServiceCall],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test extracting a playlist without entries."""

    await async_setup_component(menuai, DOMAIN, empty_media_extractor_config)
    await menuai.async_block_till_done()

    await menuai.services.async_call(
        DOMAIN,
        SERVICE_PLAY_MEDIA,
        {
            "entity_id": "media_player.bedroom",
            "media_content_type": "VIDEO",
            "media_content_id": YOUTUBE_EMPTY_PLAYLIST,
        },
    )
    await menuai.async_block_till_done()

    assert len(service_calls) == 1
    assert (
        f"Could not retrieve data for the URL: {YOUTUBE_EMPTY_PLAYLIST}" in caplog.text
    )


async def test_query_error(
    menuai: menuai,
    empty_media_extractor_config: dict[str, Any],
    service_calls: list[ServiceCall],
) -> None:
    """Test handling error with query."""

    with (
        patch(
            "menuai.components.media_extractor.YoutubeDL.extract_info",
            return_value=await async_load_json_object_fixture(
                menuai, "youtube_1_info.json", DOMAIN
            ),
        ),
        patch(
            "menuai.components.media_extractor.YoutubeDL.process_ie_result",
            side_effect=DownloadError("Message"),
        ),
    ):
        await async_setup_component(menuai, DOMAIN, empty_media_extractor_config)
        await menuai.async_block_till_done()

        await menuai.services.async_call(
            DOMAIN,
            SERVICE_PLAY_MEDIA,
            {
                "entity_id": "media_player.bedroom",
                "media_content_type": "VIDEO",
                "media_content_id": YOUTUBE_VIDEO,
            },
        )
        await menuai.async_block_till_done()

    assert len(service_calls) == 1


async def test_cookiefile_detection(
    menuai: menuai,
    mock_youtube_dl: MockYoutubeDL,
    empty_media_extractor_config: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test cookie file detection."""

    await async_setup_component(menuai, DOMAIN, empty_media_extractor_config)
    await menuai.async_block_till_done()

    cookies_dir = os.path.join(menuai.config.config_dir, "media_extractor")
    cookies_file = os.path.join(cookies_dir, "cookies.txt")

    def _write_cookies_file() -> None:
        if not os.path.exists(cookies_dir):
            os.makedirs(cookies_dir)

        with open(cookies_file, "w+", encoding="utf-8") as f:
            f.write(
                """# Netscape HTTP Cookie File

                .youtube.com TRUE / TRUE 1701708706 GPS 1
                """
            )

    await menuai.async_add_executor_job(_write_cookies_file)

    await menuai.services.async_call(
        DOMAIN,
        SERVICE_PLAY_MEDIA,
        {
            "entity_id": "media_player.bedroom",
            "media_content_type": "VIDEO",
            "media_content_id": YOUTUBE_PLAYLIST,
        },
    )
    await menuai.async_block_till_done()

    assert "Media extractor loaded cookies file" in caplog.text

    await menuai.async_add_executor_job(os.remove, cookies_file)

    await menuai.services.async_call(
        DOMAIN,
        SERVICE_PLAY_MEDIA,
        {
            "entity_id": "media_player.bedroom",
            "media_content_type": "VIDEO",
            "media_content_id": YOUTUBE_PLAYLIST,
        },
    )
    await menuai.async_block_till_done()

    assert "Media extractor didn't find cookies file" in caplog.text
