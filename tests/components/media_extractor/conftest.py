"""Common fixtures for the Media Extractor tests."""

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from menuai.components.media_extractor import DOMAIN
from menuai.core import menuai
from menuai.setup import async_setup_component

from . import MockYoutubeDL
from .const import AUDIO_QUERY


@pytest.fixture(autouse=True)
async def setup_menuai(menuai: menuai):
    """Set up the menuai integration."""
    await async_setup_component(menuai, "menuai", {})


@pytest.fixture(autouse=True)
async def setup_media_player(menuai: menuai) -> None:
    """Set up the demo media player."""
    await async_setup_component(
        menuai, "media_player", {"media_player": {"platform": "demo"}}
    )
    await menuai.async_block_till_done()


@pytest.fixture(name="mock_youtube_dl")
async def setup_mock_yt_dlp(menuai: menuai) -> MockYoutubeDL:
    """Mock YoutubeDL."""
    mock = MockYoutubeDL({})
    with patch("menuai.components.media_extractor.YoutubeDL", return_value=mock):
        yield mock


@pytest.fixture(name="empty_media_extractor_config")
def empty_media_extractor_config() -> dict[str, Any]:
    """Return base media extractor config."""
    return {DOMAIN: {}}


@pytest.fixture(name="audio_media_extractor_config")
def audio_media_extractor_config() -> dict[str, Any]:
    """Media extractor config for audio."""
    return {DOMAIN: {"default_query": AUDIO_QUERY}}


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "menuai.components.media_extractor.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry
