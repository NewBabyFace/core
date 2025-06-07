"""Tests for TTS media source."""

from http import HTTPStatus
import re
from unittest.mock import MagicMock

import pytest

from menuai.components import media_source
from menuai.components.media_player import BrowseError
from menuai.components.tts.media_source import (
    generate_media_source_id,
    parse_media_source_id,
)
from menuai.core import menuai
from menuai.setup import async_setup_component

from .common import (
    DEFAULT_LANG,
    MockResultStream,
    MockTTSEntity,
    MockTTSProvider,
    mock_config_entry_setup,
    mock_setup,
    retrieve_media,
)

from tests.typing import ClientSessionGenerator


class MSEntity(MockTTSEntity):
    """Test speech API entity."""

    get_tts_audio = MagicMock(return_value=("mp3", b""))


class MSProvider(MockTTSProvider):
    """Test speech API provider."""

    get_tts_audio = MagicMock(return_value=("mp3", b""))


@pytest.fixture(autouse=True)
async def setup_media_source(menuai: menuai) -> None:
    """Set up media source."""
    assert await async_setup_component(menuai, "media_source", {})


@pytest.mark.parametrize(
    ("mock_provider", "mock_tts_entity"),
    [(MSProvider(DEFAULT_LANG), MSEntity(DEFAULT_LANG))],
)
@pytest.mark.parametrize(
    "setup",
    [
        "mock_setup",
        "mock_config_entry_setup",
    ],
    indirect=["setup"],
)
async def test_browsing(menuai: menuai, setup: str) -> None:
    """Test browsing TTS media source."""
    item = await media_source.async_browse_media(menuai, "media-source://tts")

    assert item is not None
    assert item.title == "Text-to-speech"
    assert item.children is not None
    assert len(item.children) == 1
    assert item.can_play is False
    assert item.can_expand is True

    item_child = await media_source.async_browse_media(
        menuai, item.children[0].media_content_id
    )

    assert item_child is not None
    assert item_child.media_content_id == item.children[0].media_content_id
    assert item_child.title == "Test"
    assert item_child.children is None
    assert item_child.can_play is False
    assert item_child.can_expand is True
    assert item_child.thumbnail == "https://brands.home-assistant.io/_/test/logo.png"

    item_child = await media_source.async_browse_media(
        menuai, item.children[0].media_content_id + "?message=bla"
    )

    assert item_child is not None
    assert (
        item_child.media_content_id
        == item.children[0].media_content_id + "?message=bla"
    )
    assert item_child.title == "Test"
    assert item_child.children is None
    assert item_child.can_play is False
    assert item_child.can_expand is True

    with pytest.raises(BrowseError):
        await media_source.async_browse_media(menuai, "media-source://tts/non-existing")


@pytest.mark.parametrize(
    ("mock_provider", "extra_options"),
    [
        (MSProvider(DEFAULT_LANG), "&tts_options=%7B%22voice%22%3A%22Paulus%22%7D"),
        (MSProvider(DEFAULT_LANG), "&voice=Paulus"),
    ],
)
async def test_legacy_resolving(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    mock_provider: MSProvider,
    extra_options: str,
) -> None:
    """Test resolving legacy provider."""
    await mock_setup(menuai, mock_provider)
    mock_get_tts_audio = mock_provider.get_tts_audio

    mock_provider.has_entity = True
    root = await media_source.async_browse_media(menuai, "media-source://tts")
    assert len(root.children) == 0
    mock_provider.has_entity = False
    root = await media_source.async_browse_media(menuai, "media-source://tts")
    assert len(root.children) == 1

    mock_get_tts_audio.reset_mock()
    media_id = "media-source://tts/test?message=Hello%20World"
    media = await media_source.async_resolve_media(menuai, media_id, None)
    assert media.url.startswith("/api/tts_proxy/")
    assert media.mime_type == "audio/mpeg"
    assert await retrieve_media(menuai, menuai_client, media_id) == HTTPStatus.OK

    assert len(mock_get_tts_audio.mock_calls) == 1
    message, language = mock_get_tts_audio.mock_calls[0][1]
    assert message == "Hello World"
    assert language == "en_US"
    assert mock_get_tts_audio.mock_calls[0][2]["options"] == {}

    # Pass language and options
    mock_get_tts_audio.reset_mock()
    media_id = (
        f"media-source://tts/test?message=Bye%20World&language=de_DE{extra_options}"
    )
    media = await media_source.async_resolve_media(menuai, media_id, None)
    assert media.url.startswith("/api/tts_proxy/")
    assert media.mime_type == "audio/mpeg"
    assert await retrieve_media(menuai, menuai_client, media_id) == HTTPStatus.OK

    assert len(mock_get_tts_audio.mock_calls) == 1
    message, language = mock_get_tts_audio.mock_calls[0][1]
    assert message == "Bye World"
    assert language == "de_DE"
    assert mock_get_tts_audio.mock_calls[0][2]["options"] == {"voice": "Paulus"}


@pytest.mark.parametrize(
    ("mock_tts_entity", "extra_options"),
    [
        (MSEntity(DEFAULT_LANG), "&tts_options=%7B%22voice%22%3A%22Paulus%22%7D"),
        (MSEntity(DEFAULT_LANG), "&voice=Paulus"),
    ],
)
async def test_resolving(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    mock_tts_entity: MSEntity,
    extra_options: str,
) -> None:
    """Test resolving entity."""
    await mock_config_entry_setup(menuai, mock_tts_entity)
    mock_get_tts_audio = mock_tts_entity.get_tts_audio

    mock_get_tts_audio.reset_mock()
    media_id = "media-source://tts/tts.test?message=Hello%20World"
    media = await media_source.async_resolve_media(menuai, media_id, None)
    assert media.url.startswith("/api/tts_proxy/")
    assert media.mime_type == "audio/mpeg"
    assert await retrieve_media(menuai, menuai_client, media_id) == HTTPStatus.OK

    assert len(mock_get_tts_audio.mock_calls) == 1
    message, language = mock_get_tts_audio.mock_calls[0][1]
    assert message == "Hello World"
    assert language == "en_US"
    assert mock_get_tts_audio.mock_calls[0][2]["options"] == {}

    # Pass language and options
    mock_get_tts_audio.reset_mock()
    media_id = (
        f"media-source://tts/tts.test?message=Bye%20World&language=de_DE{extra_options}"
    )
    media = await media_source.async_resolve_media(menuai, media_id, None)
    assert media.url.startswith("/api/tts_proxy/")
    assert media.mime_type == "audio/mpeg"
    assert await retrieve_media(menuai, menuai_client, media_id) == HTTPStatus.OK

    assert len(mock_get_tts_audio.mock_calls) == 1
    message, language = mock_get_tts_audio.mock_calls[0][1]
    assert message == "Bye World"
    assert language == "de_DE"
    assert mock_get_tts_audio.mock_calls[0][2]["options"] == {"voice": "Paulus"}

    # Test with result stream
    stream = MockResultStream(menuai, "wav", b"")
    media = await media_source.async_resolve_media(menuai, stream.media_source_id, None)
    assert media.url == stream.url
    assert media.mime_type == stream.content_type

    with pytest.raises(media_source.Unresolvable):
        await media_source.async_resolve_media(
            menuai, "media-source://tts/-stream-/not-a-valid-token", None
        )


@pytest.mark.parametrize(
    ("mock_provider", "mock_tts_entity"),
    [(MSProvider(DEFAULT_LANG), MSEntity(DEFAULT_LANG))],
)
@pytest.mark.parametrize(
    ("setup", "engine"),
    [
        ("mock_setup", "test"),
        ("mock_config_entry_setup", "tts.test"),
    ],
    indirect=["setup"],
)
async def test_resolving_errors(menuai: menuai, setup: str, engine: str) -> None:
    """Test resolving."""
    # No message added
    with pytest.raises(media_source.Unresolvable):
        await media_source.async_resolve_media(menuai, "media-source://tts/test", None)

    # Non-existing provider
    with pytest.raises(
        media_source.Unresolvable, match="Provider non-existing not found"
    ):
        await media_source.async_resolve_media(
            menuai, "media-source://tts/non-existing?message=bla", None
        )

    # Non-JSON tts options
    with pytest.raises(
        media_source.Unresolvable,
        match="Invalid TTS options: Expecting property name enclosed in double quotes",
    ):
        await media_source.async_resolve_media(
            menuai,
            f"media-source://tts/{engine}?message=bla&tts_options=%7Binvalid json",
            None,
        )

    # Non-existing option
    with pytest.raises(
        media_source.Unresolvable,
        match=re.escape("Invalid options found: ['non_existing_option']"),
    ):
        await media_source.async_resolve_media(
            menuai,
            f"media-source://tts/{engine}?message=bla&tts_options=%7B%22non_existing_option%22%3A%22bla%22%7D",
            None,
        )


@pytest.mark.parametrize(
    ("setup", "result_engine"),
    [
        ("mock_setup", "test"),
        ("mock_config_entry_setup", "tts.test"),
    ],
    indirect=["setup"],
)
async def test_generate_media_source_id_and_parse_media_source_id(
    menuai: menuai,
    setup: str,
    result_engine: str,
) -> None:
    """Test media_source_id and parse_media_source_id."""
    kwargs = {
        "engine": None,
        "message": "hello",
        "language": "en_US",
        "options": {"age": 5},
        "cache": True,
    }
    media_source_id = generate_media_source_id(menuai, **kwargs)
    assert parse_media_source_id(media_source_id) == {
        "message": "hello",
        "options": {
            "engine": result_engine,
            "language": "en_US",
            "options": {"age": 5},
            "use_file_cache": True,
        },
    }

    kwargs = {
        "engine": None,
        "message": "hello",
        "language": "en_US",
        "options": {"age": [5, 6]},
        "cache": True,
    }
    media_source_id = generate_media_source_id(menuai, **kwargs)
    assert parse_media_source_id(media_source_id) == {
        "message": "hello",
        "options": {
            "engine": result_engine,
            "language": "en_US",
            "options": {"age": [5, 6]},
            "use_file_cache": True,
        },
    }

    kwargs = {
        "engine": None,
        "message": "hello",
        "language": "en_US",
        "options": {"age": {"k1": [5, 6], "k2": "v2"}},
        "cache": True,
    }
    media_source_id = generate_media_source_id(menuai, **kwargs)
    assert parse_media_source_id(media_source_id) == {
        "message": "hello",
        "options": {
            "engine": result_engine,
            "language": "en_US",
            "options": {"age": {"k1": [5, 6], "k2": "v2"}},
            "use_file_cache": True,
        },
    }
