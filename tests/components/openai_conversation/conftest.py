"""Tests helpers."""

from unittest.mock import patch

import pytest

from menuai.const import CONF_LLM_menuai_API
from menuai.core import menuai
from menuai.helpers import llm
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry


@pytest.fixture
def mock_config_entry(menuai: menuai) -> MockConfigEntry:
    """Mock a config entry."""
    entry = MockConfigEntry(
        title="OpenAI",
        domain="openai_conversation",
        data={
            "api_key": "bla",
        },
    )
    entry.add_to_menuai(menuai)
    return entry


@pytest.fixture
def mock_config_entry_with_assist(
    menuai: menuai, mock_config_entry: MockConfigEntry
) -> MockConfigEntry:
    """Mock a config entry with assist."""
    menuai.config_entries.async_update_entry(
        mock_config_entry, options={CONF_LLM_menuai_API: llm.LLM_API_ASSIST}
    )
    return mock_config_entry


@pytest.fixture
async def mock_init_component(
    menuai: menuai, mock_config_entry: MockConfigEntry
) -> None:
    """Initialize integration."""
    with patch(
        "openai.resources.models.AsyncModels.list",
    ):
        assert await async_setup_component(menuai, "openai_conversation", {})
        await menuai.async_block_till_done()


@pytest.fixture(autouse=True)
async def setup_ha(menuai: menuai) -> None:
    """Set up MenuAI."""
    assert await async_setup_component(menuai, "menuai", {})
