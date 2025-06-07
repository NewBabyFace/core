"""Provide common tests tools for conversation."""

from menuai.components import conversation
from menuai.core import menuai

from . import MockAgent

from tests.common import MockConfigEntry


def mock_conversation_agent_fixture_helper(menuai: menuai) -> MockAgent:
    """Mock agent."""
    entry = MockConfigEntry(entry_id="mock-entry")
    entry.add_to_menuai(menuai)
    agent = MockAgent(entry.entry_id, ["smurfish"])
    conversation.async_set_agent(menuai, entry, agent)
    return agent
