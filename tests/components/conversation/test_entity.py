"""Tests for conversation entity."""

from unittest.mock import patch

from menuai.components import conversation
from menuai.core import Context, menuai, State
from menuai.helpers import intent
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import mock_restore_cache


async def test_state_set_and_restore(menuai: menuai) -> None:
    """Test we set and restore state in the integration."""
    entity_id = "conversation.home_assistant"
    timestamp = "2023-01-01T23:59:59+00:00"
    mock_restore_cache(menuai, (State(entity_id, timestamp),))

    await async_setup_component(menuai, "menuai", {})
    await async_setup_component(menuai, "conversation", {})

    state = menuai.states.get(entity_id)
    assert state
    assert state.state == timestamp

    now = dt_util.utcnow()
    context = Context()

    with (
        patch(
            "menuai.components.conversation.default_agent.DefaultAgent.async_process"
        ) as mock_process,
        patch("menuai.util.dt.utcnow", return_value=now),
    ):
        intent_response = intent.IntentResponse(language="en")
        intent_response.async_set_speech("response text")
        mock_process.return_value = conversation.ConversationResult(
            response=intent_response,
        )
        await menuai.services.async_call(
            "conversation",
            "process",
            {"text": "Hello"},
            context=context,
            blocking=True,
        )

    assert len(mock_process.mock_calls) == 1

    state = menuai.states.get(entity_id)
    assert state
    assert state.state == now.isoformat()
    assert state.context is context
