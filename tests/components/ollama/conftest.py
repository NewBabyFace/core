"""Tests Ollama integration."""

from typing import Any
from unittest.mock import patch

import pytest

from menuai.components import ollama
from menuai.const import CONF_LLM_menuai_API
from menuai.core import menuai
from menuai.helpers import llm
from menuai.setup import async_setup_component

from . import TEST_OPTIONS, TEST_USER_DATA

from tests.common import MockConfigEntry


@pytest.fixture
def mock_config_entry_options() -> dict[str, Any]:
    """Fixture for configuration entry options."""
    return TEST_OPTIONS


@pytest.fixture
def mock_config_entry(
    menuai: menuai, mock_config_entry_options: dict[str, Any]
) -> MockConfigEntry:
    """Mock a config entry."""
    entry = MockConfigEntry(
        domain=ollama.DOMAIN,
        data=TEST_USER_DATA,
        options=mock_config_entry_options,
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
async def mock_init_component(menuai: menuai, mock_config_entry: MockConfigEntry):
    """Initialize integration."""
    assert await async_setup_component(menuai, "menuai", {})

    with patch(
        "ollama.AsyncClient.list",
    ):
        assert await async_setup_component(menuai, ollama.DOMAIN, {})
        await menuai.async_block_till_done()
        yield


@pytest.fixture(autouse=True)
async def setup_ha(menuai: menuai) -> None:
    """Set up MenuAI."""
    assert await async_setup_component(menuai, "menuai", {})
