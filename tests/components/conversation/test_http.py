"""The tests for the HTTP API of the Conversation component."""

from http import HTTPStatus
from typing import Any
from unittest.mock import patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.conversation import default_agent
from menuai.components.conversation.const import DATA_DEFAULT_ENTITY
from menuai.components.light import DOMAIN as LIGHT_DOMAIN
from menuai.const import ATTR_FRIENDLY_NAME
from menuai.core import menuai
from menuai.helpers import area_registry as ar, entity_registry as er, intent
from menuai.setup import async_setup_component

from . import MockAgent

from tests.common import async_mock_service
from tests.typing import ClientSessionGenerator, WebSocketGenerator

AGENT_ID_OPTIONS = [
    None,
    # Old value of conversation.HOME_ASSISTANT_AGENT,
    "menuai",
    # Current value of conversation.HOME_ASSISTANT_AGENT,
    "conversation.home_assistant",
]


class OrderBeerIntentHandler(intent.IntentHandler):
    """Handle OrderBeer intent."""

    intent_type = "OrderBeer"

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        """Return speech response."""
        beer_style = intent_obj.slots["beer_style"]["value"]
        response = intent_obj.create_response()
        response.async_set_speech(f"You ordered a {beer_style}")
        return response


@pytest.mark.parametrize("agent_id", AGENT_ID_OPTIONS)
async def test_http_processing_intent(
    menuai: menuai,
    init_components,
    menuai_client: ClientSessionGenerator,
    agent_id,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test processing intent via HTTP API."""
    # Add an alias
    entity_registry.async_get_or_create(
        "light", "demo", "1234", suggested_object_id="kitchen"
    )
    entity_registry.async_update_entity("light.kitchen", aliases={"my cool light"})
    menuai.states.async_set("light.kitchen", "off")

    calls = async_mock_service(menuai, LIGHT_DOMAIN, "turn_on")
    client = await menuai_client()
    data: dict[str, Any] = {"text": "turn on my cool light"}
    if agent_id:
        data["agent_id"] = agent_id
    resp = await client.post("/api/conversation/process", json=data)

    assert resp.status == HTTPStatus.OK
    assert len(calls) == 1
    data = await resp.json()

    assert data == snapshot


async def test_http_api_no_match(
    menuai: menuai,
    init_components,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the HTTP conversation API with an intent match failure."""
    client = await menuai_client()

    # Shouldn't match any intents
    resp = await client.post("/api/conversation/process", json={"text": "do something"})

    assert resp.status == HTTPStatus.OK
    data = await resp.json()

    assert data == snapshot
    assert data["response"]["response_type"] == "error"
    assert data["response"]["data"]["code"] == "no_intent_match"


async def test_http_api_handle_failure(
    menuai: menuai,
    init_components,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the HTTP conversation API with an error during handling."""
    client = await menuai_client()

    menuai.states.async_set("light.kitchen", "off")

    # Raise an error during intent handling
    def async_handle_error(*args, **kwargs):
        raise intent.IntentHandleError

    with patch("menuai.helpers.intent.async_handle", new=async_handle_error):
        resp = await client.post(
            "/api/conversation/process", json={"text": "turn on the kitchen"}
        )

    assert resp.status == HTTPStatus.OK
    data = await resp.json()

    assert data == snapshot
    assert data["response"]["response_type"] == "error"
    assert data["response"]["data"]["code"] == "failed_to_handle"


async def test_http_api_unexpected_failure(
    menuai: menuai,
    init_components,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the HTTP conversation API with an unexpected error during handling."""
    client = await menuai_client()

    menuai.states.async_set("light.kitchen", "off")

    # Raise an "unexpected" error during intent handling
    def async_handle_error(*args, **kwargs):
        raise intent.IntentUnexpectedError

    with patch("menuai.helpers.intent.async_handle", new=async_handle_error):
        resp = await client.post(
            "/api/conversation/process", json={"text": "turn on the kitchen"}
        )

    assert resp.status == HTTPStatus.OK
    data = await resp.json()

    assert data == snapshot
    assert data["response"]["response_type"] == "error"
    assert data["response"]["data"]["code"] == "unknown"


async def test_http_api_wrong_data(
    menuai: menuai, init_components, menuai_client: ClientSessionGenerator
) -> None:
    """Test the HTTP conversation API."""
    client = await menuai_client()

    resp = await client.post("/api/conversation/process", json={"text": 123})
    assert resp.status == HTTPStatus.BAD_REQUEST

    resp = await client.post("/api/conversation/process", json={})
    assert resp.status == HTTPStatus.BAD_REQUEST


@pytest.mark.parametrize(
    "payload",
    [
        {
            "text": "Test Text",
        },
        {
            "text": "Test Text",
            "language": "test-language",
        },
        {
            "text": "Test Text",
            "conversation_id": "test-conv-id",
        },
        {
            "text": "Test Text",
            "conversation_id": None,
        },
        {
            "text": "Test Text",
            "conversation_id": "test-conv-id",
            "language": "test-language",
        },
        {
            "text": "Test Text",
            "agent_id": "menuai",
        },
    ],
)
async def test_ws_api(
    menuai: menuai,
    init_components,
    menuai_ws_client: WebSocketGenerator,
    payload,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the Websocket conversation API."""
    client = await menuai_ws_client(menuai)

    await client.send_json_auto_id({"type": "conversation/process", **payload})

    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"] == snapshot
    assert msg["result"]["response"]["data"]["code"] == "no_intent_match"


@pytest.mark.parametrize("agent_id", AGENT_ID_OPTIONS)
async def test_ws_prepare(
    menuai: menuai, init_components, menuai_ws_client: WebSocketGenerator, agent_id
) -> None:
    """Test the Websocket prepare conversation API."""
    agent = menuai.data[DATA_DEFAULT_ENTITY]
    assert isinstance(agent, default_agent.DefaultAgent)

    # No intents should be loaded yet
    assert not agent._lang_intents.get(menuai.config.language)

    client = await menuai_ws_client(menuai)

    msg = {"type": "conversation/prepare"}
    if agent_id is not None:
        msg["agent_id"] = agent_id
    await client.send_json_auto_id(msg)

    msg = await client.receive_json()

    assert msg["success"]

    # Intents should now be load
    assert agent._lang_intents.get(menuai.config.language)


async def test_get_agent_list(
    menuai: menuai,
    init_components,
    mock_conversation_agent: MockAgent,
    mock_agent_support_all: MockAgent,
    menuai_ws_client: WebSocketGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test getting agent info."""
    client = await menuai_ws_client(menuai)

    await client.send_json_auto_id({"type": "conversation/agent/list"})
    msg = await client.receive_json()
    assert msg["type"] == "result"
    assert msg["success"]
    assert msg["result"] == snapshot

    await client.send_json_auto_id(
        {"type": "conversation/agent/list", "language": "smurfish"}
    )
    msg = await client.receive_json()
    assert msg["type"] == "result"
    assert msg["success"]
    assert msg["result"] == snapshot

    await client.send_json_auto_id(
        {"type": "conversation/agent/list", "language": "en"}
    )
    msg = await client.receive_json()
    assert msg["type"] == "result"
    assert msg["success"]
    assert msg["result"] == snapshot

    await client.send_json_auto_id(
        {"type": "conversation/agent/list", "language": "en-UK"}
    )
    msg = await client.receive_json()
    assert msg["type"] == "result"
    assert msg["success"]
    assert msg["result"] == snapshot

    await client.send_json_auto_id(
        {"type": "conversation/agent/list", "language": "de"}
    )
    msg = await client.receive_json()
    assert msg["type"] == "result"
    assert msg["success"]
    assert msg["result"] == snapshot

    await client.send_json_auto_id(
        {"type": "conversation/agent/list", "language": "de", "country": "ch"}
    )
    msg = await client.receive_json()
    assert msg["type"] == "result"
    assert msg["success"]
    assert msg["result"] == snapshot


async def test_ws_menuai_agent_debug(
    menuai: menuai,
    init_components,
    menuai_ws_client: WebSocketGenerator,
    area_registry: ar.AreaRegistry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test menuai agent debug websocket command."""
    client = await menuai_ws_client(menuai)

    kitchen_area = area_registry.async_create("kitchen")
    entity_registry.async_get_or_create(
        "light", "demo", "1234", suggested_object_id="kitchen"
    )
    entity_registry.async_update_entity(
        "light.kitchen",
        aliases={"my cool light"},
        area_id=kitchen_area.id,
    )
    await menuai.async_block_till_done()
    menuai.states.async_set("light.kitchen", "off")

    on_calls = async_mock_service(menuai, LIGHT_DOMAIN, "turn_on")
    off_calls = async_mock_service(menuai, LIGHT_DOMAIN, "turn_off")

    await client.send_json_auto_id(
        {
            "type": "conversation/agent/menuai/debug",
            "sentences": [
                "turn on my cool light",
                "turn my cool light off",
                "turn on all lights in the kitchen",
                "how many lights are on in the kitchen?",
                "this will not match anything",  # None in results
            ],
        }
    )

    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"] == snapshot

    # Last sentence should be a failed match
    assert msg["result"]["results"][-1] is None

    # Light state should not have been changed
    assert len(on_calls) == 0
    assert len(off_calls) == 0


async def test_ws_menuai_agent_debug_null_result(
    menuai: menuai,
    init_components,
    menuai_ws_client: WebSocketGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test menuai agent debug websocket command with a null result."""
    client = await menuai_ws_client(menuai)

    async def async_recognize_intent(self, user_input, *args, **kwargs):
        if user_input.text == "bad sentence":
            return None

        return await self.async_recognize(user_input, *args, **kwargs)

    with patch(
        "menuai.components.conversation.default_agent.DefaultAgent.async_recognize_intent",
        async_recognize_intent,
    ):
        await client.send_json_auto_id(
            {
                "type": "conversation/agent/menuai/debug",
                "sentences": [
                    "bad sentence",
                ],
            }
        )

        msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"] == snapshot
    assert msg["result"]["results"] == [None]


async def test_ws_menuai_agent_debug_out_of_range(
    menuai: menuai,
    init_components,
    menuai_ws_client: WebSocketGenerator,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test menuai agent debug websocket command with an out of range entity."""
    test_light = entity_registry.async_get_or_create("light", "demo", "1234")
    menuai.states.async_set(
        test_light.entity_id, "off", attributes={ATTR_FRIENDLY_NAME: "test light"}
    )

    client = await menuai_ws_client(menuai)

    # Brightness is in range (0-100)
    await client.send_json_auto_id(
        {
            "type": "conversation/agent/menuai/debug",
            "sentences": [
                "set test light brightness to 100%",
            ],
        }
    )

    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"] == snapshot

    results = msg["result"]["results"]
    assert len(results) == 1
    assert results[0]["match"]

    # Brightness is out of range
    await client.send_json_auto_id(
        {
            "type": "conversation/agent/menuai/debug",
            "sentences": [
                "set test light brightness to 1001%",
            ],
        }
    )

    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"] == snapshot

    results = msg["result"]["results"]
    assert len(results) == 1
    assert not results[0]["match"]

    # Name matched, but brightness didn't
    assert results[0]["slots"] == {"name": "test light"}
    assert results[0]["unmatched_slots"] == {"brightness": 1001}


async def test_ws_menuai_agent_debug_custom_sentence(
    menuai: menuai,
    init_components,
    menuai_ws_client: WebSocketGenerator,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test menuai agent debug websocket command with a custom sentence."""
    # Expecting testing_config/custom_sentences/en/beer.yaml
    intent.async_register(menuai, OrderBeerIntentHandler())

    client = await menuai_ws_client(menuai)

    # Brightness is in range (0-100)
    await client.send_json_auto_id(
        {
            "type": "conversation/agent/menuai/debug",
            "sentences": [
                "I'd like to order a lager, please.",
            ],
        }
    )

    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"] == snapshot

    debug_results = msg["result"].get("results", [])
    assert len(debug_results) == 1
    assert debug_results[0].get("match")
    assert debug_results[0].get("source") == "custom"
    assert debug_results[0].get("file") == "en/beer.yaml"


async def test_ws_menuai_agent_debug_sentence_trigger(
    menuai: menuai,
    init_components,
    menuai_ws_client: WebSocketGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test menuai agent debug websocket command with a sentence trigger."""
    calls = async_mock_service(menuai, "test", "automation")
    assert await async_setup_component(
        menuai,
        "automation",
        {
            "automation": {
                "trigger": {
                    "platform": "conversation",
                    "command": ["hello", "hello[ world]"],
                },
                "action": {
                    "service": "test.automation",
                    "data_template": {"data": "{{ trigger }}"},
                },
            }
        },
    )

    client = await menuai_ws_client(menuai)

    # List sentence
    await client.send_json_auto_id(
        {
            "type": "conversation/sentences/list",
        }
    )
    await menuai.async_block_till_done()

    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"] == snapshot

    # Use trigger sentence
    await client.send_json_auto_id(
        {
            "type": "conversation/agent/menuai/debug",
            "sentences": ["hello world"],
        }
    )
    await menuai.async_block_till_done()

    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"] == snapshot

    debug_results = msg["result"].get("results", [])
    assert len(debug_results) == 1
    assert debug_results[0].get("match")
    assert debug_results[0].get("source") == "trigger"
    assert debug_results[0].get("sentence_template") == "hello[ world]"

    # Trigger should not have been executed
    assert len(calls) == 0


async def test_ws_menuai_language_scores(
    menuai: menuai, init_components, menuai_ws_client: WebSocketGenerator
) -> None:
    """Test getting language support scores."""
    client = await menuai_ws_client(menuai)

    await client.send_json_auto_id(
        {"type": "conversation/agent/menuai/language_scores"}
    )

    msg = await client.receive_json()
    assert msg["success"]

    # Sanity check
    result = msg["result"]
    assert result["languages"]["en-US"] == {
        "cloud": 3,
        "focused_local": 2,
        "full_local": 3,
    }


async def test_ws_menuai_language_scores_with_filter(
    menuai: menuai, init_components, menuai_ws_client: WebSocketGenerator
) -> None:
    """Test getting language support scores with language/country filter."""
    client = await menuai_ws_client(menuai)

    # Language filter
    await client.send_json_auto_id(
        {"type": "conversation/agent/menuai/language_scores", "language": "de"}
    )

    msg = await client.receive_json()
    assert msg["success"]

    # German should be preferred
    result = msg["result"]
    assert result["preferred_language"] == "de-DE"

    # Language/country filter
    await client.send_json_auto_id(
        {
            "type": "conversation/agent/menuai/language_scores",
            "language": "en",
            "country": "GB",
        }
    )

    msg = await client.receive_json()
    assert msg["success"]

    # GB English should be preferred
    result = msg["result"]
    assert result["preferred_language"] == "en-GB"
