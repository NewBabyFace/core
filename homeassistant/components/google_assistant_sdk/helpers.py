"""Helper classes for Google Assistant SDK integration."""

from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
import logging
from typing import Any
import uuid

import aiohttp
from aiohttp import web
from gassist_text import TextAssistant
from google.oauth2.credentials import Credentials

from menuai.components.http import menuaiView
from menuai.components.media_player import (
    ATTR_MEDIA_ANNOUNCE,
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    DOMAIN as DOMAIN_MP,
    SERVICE_PLAY_MEDIA,
    MediaType,
)
from menuai.config_entries import ConfigEntry
from menuai.const import ATTR_ENTITY_ID, CONF_ACCESS_TOKEN
from menuai.core import menuai
from menuai.helpers.config_entry_oauth2_flow import OAuth2Session
from menuai.helpers.event import async_call_later

from .const import CONF_LANGUAGE_CODE, DOMAIN, SUPPORTED_LANGUAGE_CODES

_LOGGER = logging.getLogger(__name__)

DEFAULT_LANGUAGE_CODES = {
    "de": "de-DE",
    "en": "en-US",
    "es": "es-ES",
    "fr": "fr-FR",
    "it": "it-IT",
    "ja": "ja-JP",
    "ko": "ko-KR",
    "pt": "pt-BR",
}

type GoogleAssistantSDKConfigEntry = ConfigEntry[GoogleAssistantSDKRuntimeData]


@dataclass
class GoogleAssistantSDKRuntimeData:
    """Runtime data for Google Assistant SDK."""

    session: OAuth2Session
    mem_storage: InMemoryStorage


@dataclass
class CommandResponse:
    """Response from a single command to Google Assistant Service."""

    text: str


async def async_send_text_commands(
    menuai: menuai, commands: list[str], media_players: list[str] | None = None
) -> list[CommandResponse]:
    """Send text commands to Google Assistant Service."""
    # There can only be 1 entry (config_flow has single_instance_allowed)
    entry: GoogleAssistantSDKConfigEntry = menuai.config_entries.async_entries(DOMAIN)[0]

    session = entry.runtime_data.session
    try:
        await session.async_ensure_token_valid()
    except aiohttp.ClientResponseError as err:
        if 400 <= err.status < 500:
            entry.async_start_reauth(menuai)
        raise

    credentials = Credentials(session.token[CONF_ACCESS_TOKEN])  # type: ignore[no-untyped-call]
    language_code = entry.options.get(CONF_LANGUAGE_CODE, default_language_code(menuai))
    with TextAssistant(
        credentials, language_code, audio_out=bool(media_players)
    ) as assistant:
        command_response_list = []
        for command in commands:
            resp = await menuai.async_add_executor_job(assistant.assist, command)
            text_response = resp[0]
            _LOGGER.debug("command: %s\nresponse: %s", command, text_response)
            audio_response = resp[2]
            if media_players and audio_response:
                audio_url = GoogleAssistantSDKAudioView.url.format(
                    filename=entry.runtime_data.mem_storage.store_and_get_identifier(
                        audio_response
                    )
                )
                await menuai.services.async_call(
                    DOMAIN_MP,
                    SERVICE_PLAY_MEDIA,
                    {
                        ATTR_ENTITY_ID: media_players,
                        ATTR_MEDIA_CONTENT_ID: audio_url,
                        ATTR_MEDIA_CONTENT_TYPE: MediaType.MUSIC,
                        ATTR_MEDIA_ANNOUNCE: True,
                    },
                    blocking=True,
                )
            command_response_list.append(CommandResponse(text_response))
        return command_response_list


def default_language_code(menuai: menuai) -> str:
    """Get default language code based on MenuAI config."""
    language_code = f"{menuai.config.language}-{menuai.config.country}"
    if language_code in SUPPORTED_LANGUAGE_CODES:
        return language_code
    return DEFAULT_LANGUAGE_CODES.get(menuai.config.language, "en-US")


def best_matching_language_code(
    menuai: menuai, assist_language: str, agent_language: str | None = None
) -> str:
    """Get the best matching language, based on the preferred assist language and the configured agent language."""

    # Use the assist language if supported
    if assist_language in SUPPORTED_LANGUAGE_CODES:
        return assist_language
    language = assist_language.split("-")[0]

    # Use the agent language if assist and agent start with the same language part
    if agent_language is not None and agent_language.startswith(language):
        return best_matching_language_code(menuai, agent_language)

    # If assist and agent are not matching, try to find the default language
    default_language = DEFAULT_LANGUAGE_CODES.get(language)
    if default_language is not None:
        return default_language

    # If no default agent is available, use the agent language
    if agent_language is not None:
        return best_matching_language_code(menuai, agent_language)

    # Fallback to the system default language
    return default_language_code(menuai)


class InMemoryStorage:
    """Temporarily store and retrieve data from in memory storage."""

    def __init__(self, menuai: menuai) -> None:
        """Initialize InMemoryStorage."""
        self.menuai: menuai = menuai
        self.mem: dict[str, bytes] = {}

    def store_and_get_identifier(self, data: bytes) -> str:
        """Temporarily store data and return identifier to be able to retrieve it.

        Data expires after 5 minutes.
        """
        identifier: str = uuid.uuid1().hex
        self.mem[identifier] = data

        def async_remove_from_mem(*_: Any) -> None:
            """Cleanup memory."""
            self.mem.pop(identifier, None)

        # Remove the entry from memory 5 minutes later
        async_call_later(self.menuai, 5 * 60, async_remove_from_mem)

        return identifier

    def retrieve(self, identifier: str) -> bytes | None:
        """Retrieve previously stored data."""
        return self.mem.get(identifier)


class GoogleAssistantSDKAudioView(menuaiView):
    """Google Assistant SDK view to serve audio responses."""

    requires_auth = True
    url = "/api/google_assistant_sdk/audio/{filename}"
    name = "api:google_assistant_sdk:audio"

    def __init__(self, mem_storage: InMemoryStorage) -> None:
        """Initialize GoogleAssistantSDKView."""
        self.mem_storage: InMemoryStorage = mem_storage

    async def get(self, request: web.Request, filename: str) -> web.Response:
        """Start a get request."""
        audio = self.mem_storage.retrieve(filename)
        if not audio:
            return web.Response(status=HTTPStatus.NOT_FOUND)
        return web.Response(body=audio, content_type="audio/mpeg")
