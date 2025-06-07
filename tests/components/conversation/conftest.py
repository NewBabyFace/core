"""Conversation test helpers."""

from unittest.mock import patch

import pytest

from menuai.components import conversation
from menuai.components.shopping_list import intent as sl_intent
from menuai.const import MATCH_ALL
from menuai.core import menuai
from menuai.setup import async_setup_component

from . import MockAgent

from tests.common import MockConfigEntry


@pytest.fixture
def mock_agent_support_all(menuai: menuai) -> MockAgent:
    """Mock agent that supports all languages."""
    entry = MockConfigEntry(entry_id="mock-entry-support-all")
    entry.add_to_menuai(menuai)
    agent = MockAgent(entry.entry_id, MATCH_ALL)
    conversation.async_set_agent(menuai, entry, agent)
    return agent


@pytest.fixture(autouse=True)
def mock_shopping_list_io():
    """Stub out the persistence."""
    with (
        patch("menuai.components.shopping_list.ShoppingData.save"),
        patch("menuai.components.shopping_list.ShoppingData.async_load"),
    ):
        yield


@pytest.fixture
async def sl_setup(menuai: menuai):
    """Set up the shopping list."""

    entry = MockConfigEntry(domain="shopping_list")
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)

    await sl_intent.async_setup_intents(menuai)


@pytest.fixture
async def init_components(menuai: menuai):
    """Initialize relevant components with empty configs."""
    assert await async_setup_component(menuai, "menuai", {})
    assert await async_setup_component(menuai, "conversation", {})
