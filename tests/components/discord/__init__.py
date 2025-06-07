"""Tests for the Discord integration."""

from unittest.mock import AsyncMock, Mock, patch

import nextcord

from menuai.components.discord.const import DOMAIN
from menuai.const import CONF_API_TOKEN, CONF_NAME
from menuai.core import menuai

from tests.common import MockConfigEntry

TOKEN = "abc123"
NAME = "Discord Bot"

CONF_INPUT = {CONF_API_TOKEN: TOKEN}

CONF_DATA = {
    CONF_API_TOKEN: TOKEN,
    CONF_NAME: NAME,
}


def create_entry(menuai: menuai) -> MockConfigEntry:
    """Add config entry in MenuAI."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=CONF_DATA,
        unique_id="1234567890",
    )
    entry.add_to_menuai(menuai)
    return entry


def mocked_discord_info():
    """Create mocked discord."""
    mocked_discord = AsyncMock()
    mocked_discord.id = "1234567890"
    mocked_discord.name = NAME
    return patch(
        "menuai.components.discord.config_flow.nextcord.Client.application_info",
        return_value=mocked_discord,
    )


def patch_discord_login():
    """Patch discord info."""
    return patch("menuai.components.discord.config_flow.nextcord.Client.login")


def mock_exception():
    """Mock response."""
    response = Mock()
    response.status = 404
    return nextcord.HTTPException(response, "")
