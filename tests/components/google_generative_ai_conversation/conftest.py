"""Tests helpers."""

from unittest.mock import Mock, patch

import pytest

from menuai.components.google_generative_ai_conversation.conversation import (
    CONF_USE_GOOGLE_SEARCH_TOOL,
)
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_LLM_menuai_API
from menuai.core import menuai
from menuai.helpers import llm
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry


@pytest.fixture
def mock_config_entry(menuai: menuai) -> MockConfigEntry:
    """Mock a config entry."""
    entry = MockConfigEntry(
        domain="google_generative_ai_conversation",
        title="Google Generative AI Conversation",
        data={
            "api_key": "bla",
        },
    )
    entry.runtime_data = Mock()
    entry.add_to_menuai(menuai)
    return entry


@pytest.fixture
async def mock_config_entry_with_assist(
    menuai: menuai, mock_config_entry: MockConfigEntry
) -> MockConfigEntry:
    """Mock a config entry with assist."""
    with patch("google.genai.models.AsyncModels.get"):
        menuai.config_entries.async_update_entry(
            mock_config_entry, options={CONF_LLM_menuai_API: llm.LLM_API_ASSIST}
        )
        await menuai.async_block_till_done()
    return mock_config_entry


@pytest.fixture
async def mock_config_entry_with_google_search(
    menuai: menuai, mock_config_entry: MockConfigEntry
) -> MockConfigEntry:
    """Mock a config entry with assist."""
    with patch("google.genai.models.AsyncModels.get"):
        menuai.config_entries.async_update_entry(
            mock_config_entry,
            options={
                CONF_LLM_menuai_API: llm.LLM_API_ASSIST,
                CONF_USE_GOOGLE_SEARCH_TOOL: True,
            },
        )
        await menuai.async_block_till_done()
    return mock_config_entry


@pytest.fixture
async def mock_init_component(
    menuai: menuai, mock_config_entry: ConfigEntry
) -> None:
    """Initialize integration."""
    with patch("google.genai.models.AsyncModels.get"):
        assert await async_setup_component(
            menuai, "google_generative_ai_conversation", {}
        )
        await menuai.async_block_till_done()


@pytest.fixture(autouse=True)
async def setup_ha(menuai: menuai) -> None:
    """Set up MenuAI."""
    assert await async_setup_component(menuai, "menuai", {})
