"""The tests for the MaryTTS speech platform."""

from http import HTTPStatus
import io
from pathlib import Path
from unittest.mock import patch
import wave

import pytest

from menuai.components import tts
from menuai.components.media_player import (
    ATTR_MEDIA_CONTENT_ID,
    DOMAIN as DOMAIN_MP,
    SERVICE_PLAY_MEDIA,
)
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import assert_setup_component, async_mock_service
from tests.components.tts.common import retrieve_media
from tests.typing import ClientSessionGenerator


def get_empty_wav() -> bytes:
    """Get bytes for empty WAV file."""
    with io.BytesIO() as wav_io:
        with wave.open(wav_io, "wb") as wav_file:
            wav_file.setframerate(22050)
            wav_file.setsampwidth(2)
            wav_file.setnchannels(1)

        return wav_io.getvalue()


@pytest.fixture(autouse=True)
def mock_tts_cache_dir_autouse(mock_tts_cache_dir: Path) -> None:
    """Mock the TTS cache dir with empty dir."""


async def test_setup_component(menuai: menuai) -> None:
    """Test setup component."""
    config = {tts.DOMAIN: {"platform": "marytts"}}

    with assert_setup_component(1, tts.DOMAIN):
        await async_setup_component(menuai, tts.DOMAIN, config)
        await menuai.async_block_till_done()


async def test_service_say(
    menuai: menuai, menuai_client: ClientSessionGenerator
) -> None:
    """Test service call say."""
    calls = async_mock_service(menuai, DOMAIN_MP, SERVICE_PLAY_MEDIA)

    config = {tts.DOMAIN: {"platform": "marytts"}}

    with assert_setup_component(1, tts.DOMAIN):
        await async_setup_component(menuai, tts.DOMAIN, config)
        await menuai.async_block_till_done()

    with patch(
        "menuai.components.marytts.tts.MaryTTS.speak",
        return_value=get_empty_wav(),
    ) as mock_speak:
        await menuai.services.async_call(
            tts.DOMAIN,
            "marytts_say",
            {
                "entity_id": "media_player.something",
                tts.ATTR_MESSAGE: "menuai",
            },
            blocking=True,
        )

        assert (
            await retrieve_media(
                menuai, menuai_client, calls[0].data[ATTR_MEDIA_CONTENT_ID]
            )
            == HTTPStatus.OK
        )

    mock_speak.assert_called_once()
    mock_speak.assert_called_with("menuai", {})

    assert len(calls) == 1


async def test_service_say_with_effect(
    menuai: menuai, menuai_client: ClientSessionGenerator
) -> None:
    """Test service call say with effects."""
    calls = async_mock_service(menuai, DOMAIN_MP, SERVICE_PLAY_MEDIA)

    config = {tts.DOMAIN: {"platform": "marytts", "effect": {"Volume": "amount:2.0;"}}}

    with assert_setup_component(1, tts.DOMAIN):
        await async_setup_component(menuai, tts.DOMAIN, config)
        await menuai.async_block_till_done()

    with patch(
        "menuai.components.marytts.tts.MaryTTS.speak",
        return_value=get_empty_wav(),
    ) as mock_speak:
        await menuai.services.async_call(
            tts.DOMAIN,
            "marytts_say",
            {
                "entity_id": "media_player.something",
                tts.ATTR_MESSAGE: "menuai",
            },
            blocking=True,
        )

        assert (
            await retrieve_media(
                menuai, menuai_client, calls[0].data[ATTR_MEDIA_CONTENT_ID]
            )
            == HTTPStatus.OK
        )

    mock_speak.assert_called_once()
    mock_speak.assert_called_with("menuai", {"Volume": "amount:2.0;"})

    assert len(calls) == 1


async def test_service_say_http_error(
    menuai: menuai, menuai_client: ClientSessionGenerator
) -> None:
    """Test service call say."""
    calls = async_mock_service(menuai, DOMAIN_MP, SERVICE_PLAY_MEDIA)

    config = {tts.DOMAIN: {"platform": "marytts"}}

    with assert_setup_component(1, tts.DOMAIN):
        await async_setup_component(menuai, tts.DOMAIN, config)
        await menuai.async_block_till_done()

    with patch(
        "menuai.components.marytts.tts.MaryTTS.speak",
        side_effect=Exception(),
    ) as mock_speak:
        await menuai.services.async_call(
            tts.DOMAIN,
            "marytts_say",
            {
                "entity_id": "media_player.something",
                tts.ATTR_MESSAGE: "menuai",
            },
        )
        await menuai.async_block_till_done()

        assert (
            await retrieve_media(
                menuai, menuai_client, calls[0].data[ATTR_MEDIA_CONTENT_ID]
            )
            == HTTPStatus.INTERNAL_SERVER_ERROR
        )

    mock_speak.assert_called_once()
