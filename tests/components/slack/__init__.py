"""Tests for the Slack integration."""

from __future__ import annotations

import json

from menuai.components.slack.const import CONF_DEFAULT_CHANNEL, DOMAIN
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_API_KEY, CONF_NAME
from menuai.core import menuai

from tests.common import MockConfigEntry, load_fixture
from tests.test_util.aiohttp import AiohttpClientMocker

AUTH_URL = "https://slack.com/api/auth.test"

TOKEN = "abc123"
TEAM_NAME = "Test Team"
TEAM_ID = "abc123def"

CONF_INPUT = {CONF_API_KEY: TOKEN, CONF_DEFAULT_CHANNEL: "test_channel"}

CONF_DATA = CONF_INPUT | {CONF_NAME: TEAM_NAME}


def create_entry(menuai: menuai) -> ConfigEntry:
    """Add config entry in MenuAI."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=CONF_DATA,
        unique_id=TEAM_ID,
    )
    entry.add_to_menuai(menuai)
    return entry


def mock_connection(
    aioclient_mock: AiohttpClientMocker, error: str | None = None
) -> None:
    """Mock connection."""
    if error is not None:
        if error == "invalid_auth":
            aioclient_mock.post(
                AUTH_URL,
                text=json.dumps({"ok": False, "error": "invalid_auth"}),
            )
        else:
            aioclient_mock.post(
                AUTH_URL,
                text=json.dumps({"ok": False, "error": "cannot_connect"}),
            )
    else:
        aioclient_mock.post(
            AUTH_URL,
            text=load_fixture("slack/auth_test.json"),
        )


async def async_init_integration(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    skip_setup: bool = False,
    error: str | None = None,
) -> ConfigEntry:
    """Set up the Slack integration in MenuAI."""
    entry = create_entry(menuai)
    mock_connection(aioclient_mock, error)

    if not skip_setup:
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    return entry
