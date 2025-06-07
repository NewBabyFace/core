"""Tests for the conversation component."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Literal
from unittest.mock import patch

import pytest

from menuai.components import conversation
from menuai.components.conversation.models import (
    ConversationInput,
    ConversationResult,
)
from menuai.components.menuai.exposed_entities import (
    DATA_EXPOSED_ENTITIES,
    async_expose_entity,
)
from menuai.core import menuai
from menuai.helpers import chat_session, intent


class MockAgent(conversation.AbstractConversationAgent):
    """Test Agent."""

    def __init__(
        self, agent_id: str, supported_languages: list[str] | Literal["*"]
    ) -> None:
        """Initialize the agent."""
        self.agent_id = agent_id
        self.calls = []
        self.response = "Test response"
        self._supported_languages = supported_languages

    @property
    def supported_languages(self) -> list[str]:
        """Return a list of supported languages."""
        return self._supported_languages

    async def async_process(self, user_input: ConversationInput) -> ConversationResult:
        """Process some text."""
        self.calls.append(user_input)
        response = intent.IntentResponse(language=user_input.language)
        response.async_set_speech(self.response)
        return ConversationResult(
            response=response, conversation_id=user_input.conversation_id
        )


@pytest.fixture
async def mock_chat_log(menuai: menuai) -> AsyncGenerator[MockChatLog]:
    """Return mock chat logs."""
    # pylint: disable-next=contextmanager-generator-missing-cleanup
    with (
        patch(
            "menuai.components.conversation.chat_log.ChatLog",
            MockChatLog,
        ),
        chat_session.async_get_chat_session(menuai, "mock-conversation-id") as session,
        conversation.async_get_chat_log(menuai, session) as chat_log,
    ):
        yield chat_log


@dataclass
class MockChatLog(conversation.ChatLog):
    """Mock chat log."""

    _mock_tool_results: dict = field(default_factory=dict)

    def mock_tool_results(self, results: dict) -> None:
        """Set tool results."""
        self._mock_tool_results = results

    @property
    def llm_api(self):
        """Return LLM API."""
        return self._llm_api

    @llm_api.setter
    def llm_api(self, value):
        """Set LLM API."""
        self._llm_api = value

        if not value:
            return

        async def async_call_tool(tool_input):
            """Call tool."""
            if tool_input.id not in self._mock_tool_results:
                raise ValueError(f"Tool {tool_input.id} not found")
            return self._mock_tool_results[tool_input.id]

        self._llm_api.async_call_tool = async_call_tool


def expose_new(menuai: menuai, expose_new: bool) -> None:
    """Enable exposing new entities to the default agent."""
    exposed_entities = menuai.data[DATA_EXPOSED_ENTITIES]
    exposed_entities.async_set_expose_new_entities(conversation.DOMAIN, expose_new)


def expose_entity(menuai: menuai, entity_id: str, should_expose: bool) -> None:
    """Expose an entity to the default agent."""
    async_expose_entity(menuai, conversation.DOMAIN, entity_id, should_expose)
