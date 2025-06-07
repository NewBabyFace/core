"""The tests for the VoiceRSS speech platform."""

from http import HTTPStatus
from pathlib import Path
from unittest.mock import MagicMock

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
from tests.test_util.aiohttp import AiohttpClientMocker
from tests.typing import ClientSessionGenerator

URL = "https://api.voicerss.org/"
FORM_DATA = {
    "key": "1234567xx",
    "hl": "en-us",
    "c": "MP3",
    "f": "8khz_8bit_mono",
    "src": "I person is on front of your door.",
}


@pytest.fixture(autouse=True)
def tts_mutagen_mock_fixture_autouse(tts_mutagen_mock: MagicMock) -> None:
    """Mock writing tags."""


@pytest.fixture(autouse=True)
def mock_tts_cache_dir_autouse(mock_tts_cache_dir: Path) -> None:
    """Mock the TTS cache dir with empty dir."""


async def test_setup_component(menuai: menuai) -> None:
    """Test setup component."""
    config = {tts.DOMAIN: {"platform": "voicerss", "api_key": "1234567xx"}}

    with assert_setup_component(1, tts.DOMAIN):
        await async_setup_component(menuai, tts.DOMAIN, config)
        await menuai.async_block_till_done()


async def test_setup_component_without_api_key(menuai: menuai) -> None:
    """Test setup component without api key."""
    config = {tts.DOMAIN: {"platform": "voicerss"}}

    with assert_setup_component(0, tts.DOMAIN):
        await async_setup_component(menuai, tts.DOMAIN, config)
        await menuai.async_block_till_done()


async def test_service_say(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test service call say."""
    calls = async_mock_service(menuai, DOMAIN_MP, SERVICE_PLAY_MEDIA)

    aioclient_mock.post(URL, data=FORM_DATA, status=HTTPStatus.OK, content=b"test")

    config = {tts.DOMAIN: {"platform": "voicerss", "api_key": "1234567xx"}}

    with assert_setup_component(1, tts.DOMAIN):
        await async_setup_component(menuai, tts.DOMAIN, config)
        await menuai.async_block_till_done()

    await menuai.services.async_call(
        tts.DOMAIN,
        "voicerss_say",
        {
            "entity_id": "media_player.something",
            tts.ATTR_MESSAGE: "I person is on front of your door.",
        },
    )
    await menuai.async_block_till_done()

    assert len(calls) == 1
    assert (
        await retrieve_media(menuai, menuai_client, calls[0].data[ATTR_MEDIA_CONTENT_ID])
        == HTTPStatus.OK
    )
    assert len(aioclient_mock.mock_calls) == 1
    assert aioclient_mock.mock_calls[0][2] == FORM_DATA


async def test_service_say_german_config(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test service call say with german code in the config."""
    calls = async_mock_service(menuai, DOMAIN_MP, SERVICE_PLAY_MEDIA)

    form_data = {**FORM_DATA, "hl": "de-de"}
    aioclient_mock.post(URL, data=form_data, status=HTTPStatus.OK, content=b"test")

    config = {
        tts.DOMAIN: {
            "platform": "voicerss",
            "api_key": "1234567xx",
            "language": "de-de",
        }
    }

    with assert_setup_component(1, tts.DOMAIN):
        await async_setup_component(menuai, tts.DOMAIN, config)
        await menuai.async_block_till_done()

    await menuai.services.async_call(
        tts.DOMAIN,
        "voicerss_say",
        {
            "entity_id": "media_player.something",
            tts.ATTR_MESSAGE: "I person is on front of your door.",
        },
    )
    await menuai.async_block_till_done()

    assert len(calls) == 1
    assert (
        await retrieve_media(menuai, menuai_client, calls[0].data[ATTR_MEDIA_CONTENT_ID])
        == HTTPStatus.OK
    )
    assert len(aioclient_mock.mock_calls) == 1
    assert aioclient_mock.mock_calls[0][2] == form_data


async def test_service_say_german_service(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test service call say with german code in the service."""
    calls = async_mock_service(menuai, DOMAIN_MP, SERVICE_PLAY_MEDIA)

    form_data = {**FORM_DATA, "hl": "de-de"}
    aioclient_mock.post(URL, data=form_data, status=HTTPStatus.OK, content=b"test")

    config = {tts.DOMAIN: {"platform": "voicerss", "api_key": "1234567xx"}}

    with assert_setup_component(1, tts.DOMAIN):
        await async_setup_component(menuai, tts.DOMAIN, config)
        await menuai.async_block_till_done()

    await menuai.services.async_call(
        tts.DOMAIN,
        "voicerss_say",
        {
            "entity_id": "media_player.something",
            tts.ATTR_MESSAGE: "I person is on front of your door.",
            tts.ATTR_LANGUAGE: "de-de",
        },
    )
    await menuai.async_block_till_done()

    assert len(calls) == 1
    assert (
        await retrieve_media(menuai, menuai_client, calls[0].data[ATTR_MEDIA_CONTENT_ID])
        == HTTPStatus.OK
    )
    assert len(aioclient_mock.mock_calls) == 1
    assert aioclient_mock.mock_calls[0][2] == form_data


async def test_service_say_error(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test service call say with http response 400."""
    calls = async_mock_service(menuai, DOMAIN_MP, SERVICE_PLAY_MEDIA)

    aioclient_mock.post(URL, data=FORM_DATA, status=400, content=b"test")

    config = {tts.DOMAIN: {"platform": "voicerss", "api_key": "1234567xx"}}

    with assert_setup_component(1, tts.DOMAIN):
        await async_setup_component(menuai, tts.DOMAIN, config)
        await menuai.async_block_till_done()

    await menuai.services.async_call(
        tts.DOMAIN,
        "voicerss_say",
        {
            "entity_id": "media_player.something",
            tts.ATTR_MESSAGE: "I person is on front of your door.",
        },
    )
    await menuai.async_block_till_done()

    assert (
        await retrieve_media(menuai, menuai_client, calls[0].data[ATTR_MEDIA_CONTENT_ID])
        == HTTPStatus.INTERNAL_SERVER_ERROR
    )
    assert len(aioclient_mock.mock_calls) == 1
    assert aioclient_mock.mock_calls[0][2] == FORM_DATA


async def test_service_say_timeout(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test service call say with http timeout."""
    calls = async_mock_service(menuai, DOMAIN_MP, SERVICE_PLAY_MEDIA)

    aioclient_mock.post(URL, data=FORM_DATA, exc=TimeoutError())

    config = {tts.DOMAIN: {"platform": "voicerss", "api_key": "1234567xx"}}

    with assert_setup_component(1, tts.DOMAIN):
        await async_setup_component(menuai, tts.DOMAIN, config)
        await menuai.async_block_till_done()

    await menuai.services.async_call(
        tts.DOMAIN,
        "voicerss_say",
        {
            "entity_id": "media_player.something",
            tts.ATTR_MESSAGE: "I person is on front of your door.",
        },
    )
    await menuai.async_block_till_done()

    assert (
        await retrieve_media(menuai, menuai_client, calls[0].data[ATTR_MEDIA_CONTENT_ID])
        == HTTPStatus.INTERNAL_SERVER_ERROR
    )
    assert len(aioclient_mock.mock_calls) == 1
    assert aioclient_mock.mock_calls[0][2] == FORM_DATA


async def test_service_say_error_msg(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test service call say with http error api message."""
    calls = async_mock_service(menuai, DOMAIN_MP, SERVICE_PLAY_MEDIA)

    aioclient_mock.post(
        URL,
        data=FORM_DATA,
        status=HTTPStatus.OK,
        content=b"The subscription does not support SSML!",
    )

    config = {tts.DOMAIN: {"platform": "voicerss", "api_key": "1234567xx"}}

    with assert_setup_component(1, tts.DOMAIN):
        await async_setup_component(menuai, tts.DOMAIN, config)
        await menuai.async_block_till_done()

    await menuai.services.async_call(
        tts.DOMAIN,
        "voicerss_say",
        {
            "entity_id": "media_player.something",
            tts.ATTR_MESSAGE: "I person is on front of your door.",
        },
    )
    await menuai.async_block_till_done()

    assert (
        await retrieve_media(menuai, menuai_client, calls[0].data[ATTR_MEDIA_CONTENT_ID])
        == HTTPStatus.INTERNAL_SERVER_ERROR
    )
    assert len(aioclient_mock.mock_calls) == 1
    assert aioclient_mock.mock_calls[0][2] == FORM_DATA
