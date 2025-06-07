"""Test conversation."""

from __future__ import annotations

from unittest.mock import patch

from syrupy.assertion import SnapshotAssertion
from wyoming.asr import Transcript
from wyoming.handle import Handled, NotHandled
from wyoming.intent import Entity, Intent, NotRecognized

from menuai.components import conversation
from menuai.config_entries import ConfigEntry
from menuai.core import Context, menuai
from menuai.helpers import intent

from . import MockAsyncTcpClient


async def test_intent(menuai: menuai, init_wyoming_intent: ConfigEntry) -> None:
    """Test when an intent is recognized."""
    agent_id = "conversation.test_intent"

    conversation_id = "conversation-1234"
    test_intent = Intent(
        name="TestIntent",
        entities=[Entity(name="entity", value="value")],
        text="success",
    )

    class TestIntentHandler(intent.IntentHandler):
        """Test Intent Handler."""

        intent_type = "TestIntent"

        async def async_handle(self, intent_obj: intent.Intent):
            """Handle the intent."""
            assert intent_obj.slots.get("entity", {}).get("value") == "value"
            return intent_obj.create_response()

    intent.async_register(menuai, TestIntentHandler())

    with patch(
        "menuai.components.wyoming.conversation.AsyncTcpClient",
        MockAsyncTcpClient([test_intent.event()]),
    ):
        result = await conversation.async_converse(
            menuai=menuai,
            text="test text",
            conversation_id=conversation_id,
            context=Context(),
            language=menuai.config.language,
            agent_id=agent_id,
        )

    assert result.response.response_type == intent.IntentResponseType.ACTION_DONE
    assert result.response.speech, "No speech"
    assert result.response.speech.get("plain", {}).get("speech") == "success"
    assert result.conversation_id == conversation_id


async def test_intent_handle_error(
    menuai: menuai, init_wyoming_intent: ConfigEntry
) -> None:
    """Test error during handling when an intent is recognized."""
    agent_id = "conversation.test_intent"

    test_intent = Intent(name="TestIntent", entities=[], text="success")

    class TestIntentHandler(intent.IntentHandler):
        """Test Intent Handler."""

        intent_type = "TestIntent"

        async def async_handle(self, intent_obj: intent.Intent):
            """Handle the intent."""
            raise intent.IntentError

    intent.async_register(menuai, TestIntentHandler())

    with patch(
        "menuai.components.wyoming.conversation.AsyncTcpClient",
        MockAsyncTcpClient([test_intent.event()]),
    ):
        result = await conversation.async_converse(
            menuai=menuai,
            text="test text",
            conversation_id=None,
            context=Context(),
            language=menuai.config.language,
            agent_id=agent_id,
        )

    assert result.response.response_type == intent.IntentResponseType.ERROR
    assert result.response.error_code == intent.IntentResponseErrorCode.FAILED_TO_HANDLE


async def test_not_recognized(
    menuai: menuai, init_wyoming_intent: ConfigEntry
) -> None:
    """Test when an intent is not recognized."""
    agent_id = "conversation.test_intent"

    with patch(
        "menuai.components.wyoming.conversation.AsyncTcpClient",
        MockAsyncTcpClient([NotRecognized(text="failure").event()]),
    ):
        result = await conversation.async_converse(
            menuai=menuai,
            text="test text",
            conversation_id=None,
            context=Context(),
            language=menuai.config.language,
            agent_id=agent_id,
        )

    assert result.response.response_type == intent.IntentResponseType.ERROR
    assert result.response.error_code == intent.IntentResponseErrorCode.NO_INTENT_MATCH
    assert result.response.speech, "No speech"
    assert result.response.speech.get("plain", {}).get("speech") == "failure"


async def test_handle(menuai: menuai, init_wyoming_handle: ConfigEntry) -> None:
    """Test when an intent is handled."""
    agent_id = "conversation.test_handle"

    conversation_id = "conversation-1234"

    with patch(
        "menuai.components.wyoming.conversation.AsyncTcpClient",
        MockAsyncTcpClient([Handled(text="success").event()]),
    ):
        result = await conversation.async_converse(
            menuai=menuai,
            text="test text",
            conversation_id=conversation_id,
            context=Context(),
            language=menuai.config.language,
            agent_id=agent_id,
        )

    assert result.response.response_type == intent.IntentResponseType.ACTION_DONE
    assert result.response.speech, "No speech"
    assert result.response.speech.get("plain", {}).get("speech") == "success"
    assert result.conversation_id == conversation_id


async def test_not_handled(
    menuai: menuai, init_wyoming_handle: ConfigEntry
) -> None:
    """Test when an intent is not handled."""
    agent_id = "conversation.test_handle"

    with patch(
        "menuai.components.wyoming.conversation.AsyncTcpClient",
        MockAsyncTcpClient([NotHandled(text="failure").event()]),
    ):
        result = await conversation.async_converse(
            menuai=menuai,
            text="test text",
            conversation_id=None,
            context=Context(),
            language=menuai.config.language,
            agent_id=agent_id,
        )

    assert result.response.response_type == intent.IntentResponseType.ERROR
    assert result.response.error_code == intent.IntentResponseErrorCode.FAILED_TO_HANDLE
    assert result.response.speech, "No speech"
    assert result.response.speech.get("plain", {}).get("speech") == "failure"


async def test_connection_lost(
    menuai: menuai, init_wyoming_handle: ConfigEntry, snapshot: SnapshotAssertion
) -> None:
    """Test connection to client is lost."""
    agent_id = "conversation.test_handle"

    with patch(
        "menuai.components.wyoming.conversation.AsyncTcpClient",
        MockAsyncTcpClient([None]),
    ):
        result = await conversation.async_converse(
            menuai=menuai,
            text="test text",
            conversation_id=None,
            context=Context(),
            language=menuai.config.language,
            agent_id=agent_id,
        )

    assert result.response.response_type == intent.IntentResponseType.ERROR
    assert result.response.error_code == intent.IntentResponseErrorCode.UNKNOWN
    assert result.response.speech, "No speech"
    assert result.response.speech.get("plain", {}).get("speech") == snapshot


async def test_oserror(
    menuai: menuai, init_wyoming_handle: ConfigEntry, snapshot: SnapshotAssertion
) -> None:
    """Test connection error."""
    agent_id = "conversation.test_handle"

    mock_client = MockAsyncTcpClient([Transcript("success").event()])

    with (
        patch(
            "menuai.components.wyoming.conversation.AsyncTcpClient", mock_client
        ),
        patch.object(mock_client, "read_event", side_effect=OSError("Boom!")),
    ):
        result = await conversation.async_converse(
            menuai=menuai,
            text="test text",
            conversation_id=None,
            context=Context(),
            language=menuai.config.language,
            agent_id=agent_id,
        )

    assert result.response.response_type == intent.IntentResponseType.ERROR
    assert result.response.error_code == intent.IntentResponseErrorCode.UNKNOWN
    assert result.response.speech, "No speech"
    assert result.response.speech.get("plain", {}).get("speech") == snapshot
