"""Tests for WebSocket API commands."""

import asyncio
from copy import deepcopy
import logging
from typing import Any
from unittest.mock import ANY, AsyncMock, Mock, patch

import pytest
import voluptuous as vol

from menuai import loader
from menuai.components.device_automation import toggle_entity
from menuai.components.websocket_api import const
from menuai.components.websocket_api.auth import (
    TYPE_AUTH,
    TYPE_AUTH_OK,
    TYPE_AUTH_REQUIRED,
)
from menuai.components.websocket_api.const import FEATURE_COALESCE_MESSAGES, URL
from menuai.config_entries import ConfigEntryState
from menuai.const import SIGNAL_BOOTSTRAP_INTEGRATIONS
from menuai.core import Context, menuai, State, SupportsResponse, callback
from menuai.exceptions import menuaiError, ServiceValidationError
from menuai.helpers import device_registry as dr
from menuai.helpers.dispatcher import async_dispatcher_send
from menuai.helpers.event import async_track_state_change_event
from menuai.loader import async_get_integration
from menuai.setup import async_set_domains_to_be_loaded, async_setup_component
from menuai.util.json import json_loads

from tests.common import (
    MockConfigEntry,
    MockEntity,
    MockEntityPlatform,
    MockModule,
    MockUser,
    async_mock_service,
    mock_integration,
    mock_platform,
)
from tests.typing import (
    ClientSessionGenerator,
    MockHAClientWebSocket,
    WebSocketGenerator,
)

STATE_KEY_SHORT_NAMES = {
    "entity_id": "e",
    "state": "s",
    "last_changed": "lc",
    "last_updated": "lu",
    "context": "c",
    "attributes": "a",
}
STATE_KEY_LONG_NAMES = {v: k for k, v in STATE_KEY_SHORT_NAMES.items()}


@pytest.fixture
def fake_integration(menuai: menuai):
    """Set up a mock integration with device automation support."""
    DOMAIN = "fake_integration"

    menuai.config.components.add(DOMAIN)

    mock_platform(
        menuai,
        f"{DOMAIN}.device_action",
        Mock(
            ACTION_SCHEMA=toggle_entity.ACTION_SCHEMA.extend(
                {vol.Required("domain"): DOMAIN}
            ),
            spec=["ACTION_SCHEMA"],
        ),
    )


def _apply_entities_changes(state_dict: dict, change_dict: dict) -> None:
    """Apply a diff set to a dict.

    Port of the client side merging
    """
    additions = change_dict.get("+", {})
    if "lc" in additions:
        additions["lu"] = additions["lc"]
    if attributes := additions.pop("a", None):
        state_dict["attributes"].update(attributes)
    if context := additions.pop("c", None):
        if isinstance(context, str):
            state_dict["context"]["id"] = context
        else:
            state_dict["context"].update(context)
    for k, v in additions.items():
        state_dict[STATE_KEY_LONG_NAMES[k]] = v
    for key, items in change_dict.get("-", {}).items():
        for item in items:
            del state_dict[STATE_KEY_LONG_NAMES[key]][item]


async def test_fire_event(
    menuai: menuai, websocket_client: MockHAClientWebSocket
) -> None:
    """Test fire event command."""
    runs = []

    async def event_handler(event):
        runs.append(event)

    menuai.bus.async_listen_once("event_type_test", event_handler)

    await websocket_client.send_json_auto_id(
        {
            "type": "fire_event",
            "event_type": "event_type_test",
            "event_data": {"hello": "world"},
        }
    )

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]

    assert len(runs) == 1

    assert runs[0].event_type == "event_type_test"
    assert runs[0].data == {"hello": "world"}


async def test_fire_event_without_data(
    menuai: menuai, websocket_client: MockHAClientWebSocket
) -> None:
    """Test fire event command."""
    runs = []

    async def event_handler(event):
        runs.append(event)

    menuai.bus.async_listen_once("event_type_test", event_handler)

    await websocket_client.send_json_auto_id(
        {
            "type": "fire_event",
            "event_type": "event_type_test",
        }
    )

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]

    assert len(runs) == 1

    assert runs[0].event_type == "event_type_test"
    assert runs[0].data == {}


async def test_call_service(
    menuai: menuai, websocket_client: MockHAClientWebSocket
) -> None:
    """Test call service command."""
    calls = async_mock_service(menuai, "domain_test", "test_service")

    await websocket_client.send_json_auto_id(
        {
            "type": "call_service",
            "domain": "domain_test",
            "service": "test_service",
            "service_data": {"hello": "world"},
        }
    )

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]

    assert len(calls) == 1
    call = calls[0]

    assert call.domain == "domain_test"
    assert call.service == "test_service"
    assert call.data == {"hello": "world"}
    assert call.context.as_dict() == msg["result"]["context"]


async def test_return_response_error(menuai: menuai, websocket_client) -> None:
    """Test return_response=True errors when service has no response."""
    menuai.services.async_register(
        "domain_test", "test_service_with_no_response", lambda x: None
    )
    await websocket_client.send_json_auto_id(
        {
            "type": "call_service",
            "domain": "domain_test",
            "service": "test_service_with_no_response",
            "service_data": {"hello": "world"},
            "return_response": True,
        },
    )
    msg = await websocket_client.receive_json()

    assert msg["type"] == const.TYPE_RESULT
    assert not msg["success"]
    assert msg["error"]["code"] == "service_validation_error"


@pytest.mark.parametrize("command", ["call_service", "call_service_action"])
async def test_call_service_blocking(
    menuai: menuai, websocket_client: MockHAClientWebSocket, command
) -> None:
    """Test call service commands block, except for menuai restart / stop."""
    async_mock_service(
        menuai,
        "domain_test",
        "test_service",
        response={"hello": "world"},
        supports_response=SupportsResponse.OPTIONAL,
    )
    with patch(
        "menuai.core.ServiceRegistry.async_call", autospec=True
    ) as mock_call:
        mock_call.return_value = {"foo": "bar"}
        await websocket_client.send_json_auto_id(
            {
                "type": "call_service",
                "domain": "domain_test",
                "service": "test_service",
                "service_data": {"hello": "world"},
                "return_response": True,
            },
        )
        msg = await websocket_client.receive_json()

    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]
    assert msg["result"]["response"] == {"foo": "bar"}
    mock_call.assert_called_once_with(
        ANY,
        "domain_test",
        "test_service",
        {"hello": "world"},
        blocking=True,
        context=ANY,
        target=ANY,
        return_response=True,
    )

    with patch(
        "menuai.core.ServiceRegistry.async_call", autospec=True
    ) as mock_call:
        mock_call.return_value = None
        await websocket_client.send_json_auto_id(
            {
                "type": "call_service",
                "domain": "domain_test",
                "service": "test_service",
                "service_data": {"hello": "world"},
            },
        )
        msg = await websocket_client.receive_json()

    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]
    mock_call.assert_called_once_with(
        ANY,
        "domain_test",
        "test_service",
        {"hello": "world"},
        blocking=True,
        context=ANY,
        target=ANY,
        return_response=False,
    )

    async_mock_service(menuai, "menuai", "test_service")
    with patch(
        "menuai.core.ServiceRegistry.async_call", autospec=True
    ) as mock_call:
        mock_call.return_value = None
        await websocket_client.send_json_auto_id(
            {
                "type": "call_service",
                "domain": "menuai",
                "service": "test_service",
            },
        )
        msg = await websocket_client.receive_json()

    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]
    mock_call.assert_called_once_with(
        ANY,
        "menuai",
        "test_service",
        ANY,
        blocking=True,
        context=ANY,
        target=ANY,
        return_response=False,
    )

    async_mock_service(menuai, "menuai", "restart")
    with patch(
        "menuai.core.ServiceRegistry.async_call", autospec=True
    ) as mock_call:
        mock_call.return_value = None
        await websocket_client.send_json_auto_id(
            {
                "type": "call_service",
                "domain": "menuai",
                "service": "restart",
            },
        )
        msg = await websocket_client.receive_json()

    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]
    mock_call.assert_called_once_with(
        ANY,
        "menuai",
        "restart",
        ANY,
        blocking=True,
        context=ANY,
        target=ANY,
        return_response=False,
    )


async def test_call_service_target(
    menuai: menuai, websocket_client: MockHAClientWebSocket
) -> None:
    """Test call service command with target."""
    calls = async_mock_service(menuai, "domain_test", "test_service")

    await websocket_client.send_json_auto_id(
        {
            "type": "call_service",
            "domain": "domain_test",
            "service": "test_service",
            "service_data": {"hello": "world"},
            "target": {
                "entity_id": ["entity.one", "entity.two"],
                "device_id": "deviceid",
            },
        }
    )

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]

    assert len(calls) == 1
    call = calls[0]

    assert call.domain == "domain_test"
    assert call.service == "test_service"
    assert call.data == {
        "hello": "world",
        "entity_id": ["entity.one", "entity.two"],
        "device_id": ["deviceid"],
    }
    assert call.context.as_dict() == msg["result"]["context"]


async def test_call_service_target_template(
    menuai: menuai, websocket_client
) -> None:
    """Test call service command with target does not allow template."""
    await websocket_client.send_json_auto_id(
        {
            "type": "call_service",
            "domain": "domain_test",
            "service": "test_service",
            "service_data": {"hello": "world"},
            "target": {
                "entity_id": "{{ 1 }}",
            },
        }
    )

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert not msg["success"]
    assert msg["error"]["code"] == const.ERR_INVALID_FORMAT


async def test_call_service_not_found(
    menuai: menuai, websocket_client: MockHAClientWebSocket
) -> None:
    """Test call service command."""
    await websocket_client.send_json_auto_id(
        {
            "type": "call_service",
            "domain": "domain_test",
            "service": "test_service",
            "service_data": {"hello": "world"},
        }
    )

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert not msg["success"]
    assert msg["error"]["code"] == const.ERR_NOT_FOUND
    assert msg["error"]["message"] == "Service domain_test.test_service not found."
    assert msg["error"]["translation_placeholders"] == {
        "domain": "domain_test",
        "service": "test_service",
    }
    assert msg["error"]["translation_key"] == "service_not_found"
    assert msg["error"]["translation_domain"] == "menuai"


async def test_call_service_child_not_found(
    menuai: menuai, websocket_client
) -> None:
    """Test not reporting not found errors if it's not the called service."""

    async def serv_handler(call):
        await menuai.services.async_call("non", "existing")

    menuai.services.async_register("domain_test", "test_service", serv_handler)

    await websocket_client.send_json_auto_id(
        {
            "type": "call_service",
            "domain": "domain_test",
            "service": "test_service",
            "service_data": {"hello": "world"},
        }
    )

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert not msg["success"]
    assert msg["error"]["code"] == const.ERR_HOME_ASSISTANT_ERROR
    assert (
        msg["error"]["message"] == "Service non.existing called service "
        "domain_test.test_service which was not found."
    )
    assert msg["error"]["translation_placeholders"] == {
        "domain": "domain_test",
        "service": "test_service",
        "child_domain": "non",
        "child_service": "existing",
    }
    assert msg["error"]["translation_key"] == "child_service_not_found"
    assert msg["error"]["translation_domain"] == "websocket_api"


async def test_call_service_schema_validation_error(
    menuai: menuai, websocket_client
) -> None:
    """Test call service command with invalid service data."""

    calls = []
    service_schema = vol.Schema(
        {
            vol.Required("message"): str,
        }
    )

    @callback
    def service_call(call):
        calls.append(call)

    menuai.services.async_register(
        "domain_test",
        "test_service",
        service_call,
        schema=service_schema,
    )

    await websocket_client.send_json_auto_id(
        {
            "type": "call_service",
            "domain": "domain_test",
            "service": "test_service",
            "service_data": {},
        }
    )
    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert not msg["success"]
    assert msg["error"]["code"] == const.ERR_INVALID_FORMAT

    await websocket_client.send_json_auto_id(
        {
            "type": "call_service",
            "domain": "domain_test",
            "service": "test_service",
            "service_data": {"extra_key": "not allowed"},
        }
    )
    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert not msg["success"]
    assert msg["error"]["code"] == const.ERR_INVALID_FORMAT

    await websocket_client.send_json_auto_id(
        {
            "type": "call_service",
            "domain": "domain_test",
            "service": "test_service",
            "service_data": {"message": []},
        }
    )
    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert not msg["success"]
    assert msg["error"]["code"] == const.ERR_INVALID_FORMAT

    assert len(calls) == 0


@pytest.mark.parametrize("ignore_translations_for_mock_domains", ["test"])
async def test_call_service_error(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    websocket_client: MockHAClientWebSocket,
) -> None:
    """Test call service command with error."""
    caplog.set_level(logging.ERROR)

    @callback
    def ha_error_call(_):
        raise menuaiError(
            "error_message",
            translation_domain="test",
            translation_key="custom_error",
            translation_placeholders={"option": "bla"},
        )

    menuai.services.async_register("domain_test", "ha_error", ha_error_call)

    @callback
    def service_error_call(_):
        raise ServiceValidationError(
            "error_message",
            translation_domain="test",
            translation_key="custom_error",
            translation_placeholders={"option": "bla"},
        )

    menuai.services.async_register("domain_test", "service_error", service_error_call)

    async def unknown_error_call(_):
        raise ValueError("value_error")

    menuai.services.async_register("domain_test", "unknown_error", unknown_error_call)

    await websocket_client.send_json_auto_id(
        {
            "type": "call_service",
            "domain": "domain_test",
            "service": "ha_error",
        }
    )

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"] is False
    assert msg["error"]["code"] == "home_assistant_error"
    assert msg["error"]["message"] == "error_message"
    assert msg["error"]["translation_placeholders"] == {"option": "bla"}
    assert msg["error"]["translation_key"] == "custom_error"
    assert msg["error"]["translation_domain"] == "test"
    assert "Traceback" not in caplog.text

    await websocket_client.send_json_auto_id(
        {
            "type": "call_service",
            "domain": "domain_test",
            "service": "service_error",
        }
    )

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"] is False
    assert msg["error"]["code"] == "service_validation_error"
    assert msg["error"]["message"] == "Validation error: error_message"
    assert msg["error"]["translation_placeholders"] == {"option": "bla"}
    assert msg["error"]["translation_key"] == "custom_error"
    assert msg["error"]["translation_domain"] == "test"
    assert "Traceback" not in caplog.text

    await websocket_client.send_json_auto_id(
        {
            "type": "call_service",
            "domain": "domain_test",
            "service": "unknown_error",
        }
    )

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"] is False
    assert msg["error"]["code"] == "unknown_error"
    assert msg["error"]["message"] == "value_error"
    assert "Traceback" in caplog.text


async def test_subscribe_unsubscribe_events(
    menuai: menuai, websocket_client
) -> None:
    """Test subscribe/unsubscribe events command."""
    init_count = sum(menuai.bus.async_listeners().values())

    await websocket_client.send_json_auto_id(
        {"type": "subscribe_events", "event_type": "test_event"}
    )

    msg = await websocket_client.receive_json()
    subscription = msg["id"]
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]

    # Verify we have a new listener
    assert sum(menuai.bus.async_listeners().values()) == init_count + 1

    menuai.bus.async_fire("ignore_event")
    menuai.bus.async_fire("test_event", {"hello": "world"})
    menuai.bus.async_fire("ignore_event")

    async with asyncio.timeout(3):
        msg = await websocket_client.receive_json()

    assert msg["id"] == subscription
    assert msg["type"] == "event"
    event = msg["event"]

    assert event["event_type"] == "test_event"
    assert event["data"] == {"hello": "world"}
    assert event["origin"] == "LOCAL"

    await websocket_client.send_json_auto_id(
        {"type": "unsubscribe_events", "subscription": subscription}
    )

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]

    # Check our listener got unsubscribed
    assert sum(menuai.bus.async_listeners().values()) == init_count


async def test_get_states(
    menuai: menuai, websocket_client: MockHAClientWebSocket
) -> None:
    """Test get_states command."""
    menuai.states.async_set("greeting.hello", "world")
    menuai.states.async_set("greeting.bye", "universe")

    await websocket_client.send_json_auto_id({"type": "get_states"})

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]

    states = [state.as_dict() for state in menuai.states.async_all()]

    assert msg["result"] == states


async def test_get_services(
    menuai: menuai, websocket_client: MockHAClientWebSocket
) -> None:
    """Test get_services command."""
    for id_ in (5, 6):
        await websocket_client.send_json({"id": id_, "type": "get_services"})

        msg = await websocket_client.receive_json()
        assert msg["id"] == id_
        assert msg["type"] == const.TYPE_RESULT
        assert msg["success"]
        assert msg["result"].keys() == menuai.services.async_services().keys()


async def test_get_config(
    menuai: menuai, websocket_client: MockHAClientWebSocket
) -> None:
    """Test get_config command."""
    await websocket_client.send_json_auto_id({"type": "get_config"})

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]

    result = msg["result"]
    ignore_order_keys = (
        "components",
        "allowlist_external_dirs",
        "whitelist_external_dirs",
        "allowlist_external_urls",
    )
    config = menuai.config.as_dict()

    for key in ignore_order_keys:
        if key in result:
            result[key] = set(result[key])
            config[key] = set(config[key])

    assert result == config


async def test_ping(websocket_client: MockHAClientWebSocket) -> None:
    """Test get_panels command."""
    await websocket_client.send_json_auto_id({"type": "ping"})

    msg = await websocket_client.receive_json()
    assert msg["type"] == "pong"


async def test_call_service_context_with_user(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    menuai_access_token: str,
) -> None:
    """Test that the user is set in the service call context."""
    assert await async_setup_component(menuai, "websocket_api", {})

    calls = async_mock_service(menuai, "domain_test", "test_service")
    client = await menuai_client_no_auth()

    async with client.ws_connect(URL) as ws:
        auth_msg = await ws.receive_json()
        assert auth_msg["type"] == TYPE_AUTH_REQUIRED

        await ws.send_json({"type": TYPE_AUTH, "access_token": menuai_access_token})

        auth_msg = await ws.receive_json()
        assert auth_msg["type"] == TYPE_AUTH_OK

        await ws.send_json(
            {
                "id": 5,
                "type": "call_service",
                "domain": "domain_test",
                "service": "test_service",
                "service_data": {"hello": "world"},
            }
        )

        msg = await ws.receive_json()
        assert msg["success"]

        refresh_token = menuai.auth.async_validate_access_token(menuai_access_token)

        assert len(calls) == 1
        call = calls[0]
        assert call.domain == "domain_test"
        assert call.service == "test_service"
        assert call.data == {"hello": "world"}
        assert call.context.user_id == refresh_token.user.id


async def test_subscribe_requires_admin(
    websocket_client: MockHAClientWebSocket, menuai_admin_user: MockUser
) -> None:
    """Test subscribing events without being admin."""
    menuai_admin_user.groups = []
    await websocket_client.send_json_auto_id(
        {"type": "subscribe_events", "event_type": "test_event"}
    )

    msg = await websocket_client.receive_json()
    assert not msg["success"]
    assert msg["error"]["code"] == const.ERR_UNAUTHORIZED


async def test_states_filters_visible(
    menuai: menuai, menuai_admin_user: MockUser, websocket_client
) -> None:
    """Test we only get entities that we're allowed to see."""
    menuai_admin_user.groups = []
    menuai_admin_user.mock_policy({"entities": {"entity_ids": {"test.entity": True}}})
    menuai.states.async_set("test.entity", "hello")
    menuai.states.async_set("test.not_visible_entity", "invisible")
    await websocket_client.send_json_auto_id({"type": "get_states"})

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]

    assert len(msg["result"]) == 1
    assert msg["result"][0]["entity_id"] == "test.entity"


async def test_get_states_not_allows_nan(
    menuai: menuai, websocket_client: MockHAClientWebSocket
) -> None:
    """Test get_states command converts NaN to None."""
    menuai.states.async_set("greeting.hello", "world")
    menuai.states.async_set("greeting.bad", "data", {"hello": float("NaN")})
    menuai.states.async_set("greeting.bye", "universe")

    await websocket_client.send_json_auto_id({"type": "get_states"})
    bad = dict(menuai.states.get("greeting.bad").as_dict())
    bad["attributes"] = dict(bad["attributes"])
    bad["attributes"]["hello"] = None

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]
    assert msg["result"] == [
        menuai.states.get("greeting.hello").as_dict(),
        bad,
        menuai.states.get("greeting.bye").as_dict(),
    ]


async def test_subscribe_unsubscribe_events_whitelist(
    menuai: menuai,
    websocket_client: MockHAClientWebSocket,
    menuai_admin_user: MockUser,
) -> None:
    """Test subscribe/unsubscribe events on whitelist."""
    menuai_admin_user.groups = []

    await websocket_client.send_json_auto_id(
        {"type": "subscribe_events", "event_type": "not-in-whitelist"}
    )

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert not msg["success"]
    assert msg["error"]["code"] == "unauthorized"

    await websocket_client.send_json_auto_id(
        {"type": "subscribe_events", "event_type": "themes_updated"}
    )

    msg = await websocket_client.receive_json()
    themes_updated_subscription = msg["id"]
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]

    menuai.bus.async_fire("themes_updated")

    async with asyncio.timeout(3):
        msg = await websocket_client.receive_json()

    assert msg["id"] == themes_updated_subscription
    assert msg["type"] == "event"
    event = msg["event"]
    assert event["event_type"] == "themes_updated"
    assert event["origin"] == "LOCAL"


async def test_subscribe_unsubscribe_events_state_changed(
    menuai: menuai,
    websocket_client: MockHAClientWebSocket,
    menuai_admin_user: MockUser,
) -> None:
    """Test subscribe/unsubscribe state_changed events."""
    menuai_admin_user.groups = []
    menuai_admin_user.mock_policy({"entities": {"entity_ids": {"light.permitted": True}}})

    await websocket_client.send_json_auto_id(
        {"type": "subscribe_events", "event_type": "state_changed"}
    )

    msg = await websocket_client.receive_json()
    subscription = msg["id"]
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]

    menuai.states.async_set("light.not_permitted", "on")
    menuai.states.async_set("light.permitted", "on")

    msg = await websocket_client.receive_json()
    assert msg["id"] == subscription
    assert msg["type"] == "event"
    assert msg["event"]["event_type"] == "state_changed"
    assert msg["event"]["data"]["entity_id"] == "light.permitted"


async def test_subscribe_entities_with_unserializable_state(
    menuai: menuai,
    websocket_client: MockHAClientWebSocket,
    menuai_admin_user: MockUser,
) -> None:
    """Test subscribe entities with an unserializeable state."""

    class CannotSerializeMe:
        """Cannot serialize this."""

        def __init__(self) -> None:
            """Init cannot serialize this."""

    menuai.states.async_set("light.permitted", "off", {"color": "red"})
    menuai.states.async_set(
        "light.cannot_serialize",
        "off",
        {"color": "red", "cannot_serialize": CannotSerializeMe()},
    )
    original_state = menuai.states.get("light.cannot_serialize")
    assert isinstance(original_state, State)
    state_dict = {
        "attributes": dict(original_state.attributes),
        "context": dict(original_state.context.as_dict()),
        "entity_id": original_state.entity_id,
        "last_changed": original_state.last_changed.isoformat(),
        "last_updated": original_state.last_updated.isoformat(),
        "state": original_state.state,
    }
    menuai_admin_user.groups = []
    menuai_admin_user.mock_policy(
        {
            "entities": {
                "entity_ids": {"light.permitted": True, "light.cannot_serialize": True}
            }
        }
    )

    await websocket_client.send_json_auto_id({"type": "subscribe_entities"})

    msg = await websocket_client.receive_json()
    subscription = msg["id"]
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]

    msg = await websocket_client.receive_json()
    assert msg["id"] == subscription
    assert msg["type"] == "event"
    assert msg["event"] == {
        "a": {
            "light.permitted": {
                "a": {"color": "red"},
                "c": ANY,
                "lc": ANY,
                "s": "off",
            }
        }
    }
    menuai.states.async_set("light.permitted", "on", {"effect": "help"})
    msg = await websocket_client.receive_json()
    assert msg["id"] == subscription
    assert msg["type"] == "event"
    assert msg["event"] == {
        "c": {
            "light.permitted": {
                "+": {
                    "a": {"effect": "help"},
                    "c": ANY,
                    "lc": ANY,
                    "s": "on",
                },
                "-": {"a": ["color"]},
            }
        }
    }
    menuai.states.async_set("light.cannot_serialize", "on", {"effect": "help"})
    msg = await websocket_client.receive_json()
    assert msg["id"] == subscription
    assert msg["type"] == "event"
    # Order does not matter
    msg["event"]["c"]["light.cannot_serialize"]["-"]["a"] = set(
        msg["event"]["c"]["light.cannot_serialize"]["-"]["a"]
    )
    assert msg["event"] == {
        "c": {
            "light.cannot_serialize": {
                "+": {"a": {"effect": "help"}, "c": ANY, "lc": ANY, "s": "on"},
                "-": {"a": {"color", "cannot_serialize"}},
            }
        }
    }
    change_set = msg["event"]["c"]["light.cannot_serialize"]
    _apply_entities_changes(state_dict, change_set)
    assert state_dict == {
        "attributes": {"effect": "help"},
        "context": {
            "id": ANY,
            "parent_id": None,
            "user_id": None,
        },
        "entity_id": "light.cannot_serialize",
        "last_changed": ANY,
        "last_updated": ANY,
        "state": "on",
    }
    menuai.states.async_set(
        "light.cannot_serialize",
        "off",
        {"color": "red", "cannot_serialize": CannotSerializeMe()},
    )
    msg = await websocket_client.receive_json()
    assert msg["id"] == subscription
    assert msg["type"] == "result"
    assert msg["error"] == {
        "code": "unknown_error",
        "message": "Invalid JSON in response",
    }


async def test_subscribe_unsubscribe_entities(
    menuai: menuai,
    websocket_client: MockHAClientWebSocket,
    menuai_admin_user: MockUser,
) -> None:
    """Test subscribe/unsubscribe entities."""

    menuai.states.async_set("light.permitted", "off", {"color": "red"})
    original_state = menuai.states.get("light.permitted")
    assert isinstance(original_state, State)
    state_dict = {
        "attributes": dict(original_state.attributes),
        "context": dict(original_state.context.as_dict()),
        "entity_id": original_state.entity_id,
        "last_changed": original_state.last_changed.isoformat(),
        "last_updated": original_state.last_updated.isoformat(),
        "state": original_state.state,
    }
    menuai_admin_user.groups = []
    menuai_admin_user.mock_policy({"entities": {"entity_ids": {"light.permitted": True}}})
    assert not menuai_admin_user.is_admin

    await websocket_client.send_json_auto_id({"type": "subscribe_entities"})

    msg = await websocket_client.receive_json()
    subscription = msg["id"]
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]

    msg = await websocket_client.receive_json()
    assert msg["id"] == subscription
    assert msg["type"] == "event"
    assert isinstance(msg["event"]["a"]["light.permitted"]["c"], str)
    assert msg["event"] == {
        "a": {
            "light.permitted": {
                "a": {"color": "red"},
                "c": ANY,
                "lc": ANY,
                "s": "off",
            }
        }
    }
    menuai.states.async_set("light.not_permitted", "on")
    menuai.states.async_set("light.permitted", "on", {"color": "blue"})
    menuai.states.async_set("light.permitted", "on", {"effect": "help"})
    menuai.states.async_set(
        "light.permitted", "on", {"effect": "help", "color": ["blue", "green"]}
    )
    menuai.states.async_remove("light.permitted")
    menuai.states.async_set("light.permitted", "on", {"effect": "help", "color": "blue"})

    msg = await websocket_client.receive_json()
    assert msg["id"] == subscription
    assert msg["type"] == "event"
    assert msg["event"] == {
        "c": {
            "light.permitted": {
                "+": {
                    "a": {"color": "blue"},
                    "c": ANY,
                    "lc": ANY,
                    "s": "on",
                }
            }
        }
    }

    change_set = msg["event"]["c"]["light.permitted"]
    additions = deepcopy(change_set["+"])
    _apply_entities_changes(state_dict, change_set)
    assert state_dict == {
        "attributes": {"color": "blue"},
        "context": {
            "id": additions["c"],
            "parent_id": None,
            "user_id": None,
        },
        "entity_id": "light.permitted",
        "last_changed": additions["lc"],
        "last_updated": additions["lc"],
        "state": "on",
    }

    msg = await websocket_client.receive_json()
    assert msg["id"] == subscription
    assert msg["type"] == "event"
    assert msg["event"] == {
        "c": {
            "light.permitted": {
                "+": {
                    "a": {"effect": "help"},
                    "c": ANY,
                    "lu": ANY,
                },
                "-": {"a": ["color"]},
            }
        }
    }

    change_set = msg["event"]["c"]["light.permitted"]
    additions = deepcopy(change_set["+"])
    _apply_entities_changes(state_dict, change_set)

    assert state_dict == {
        "attributes": {"effect": "help"},
        "context": {
            "id": additions["c"],
            "parent_id": None,
            "user_id": None,
        },
        "entity_id": "light.permitted",
        "last_changed": ANY,
        "last_updated": additions["lu"],
        "state": "on",
    }

    msg = await websocket_client.receive_json()
    assert msg["id"] == subscription
    assert msg["type"] == "event"
    assert msg["event"] == {
        "c": {
            "light.permitted": {
                "+": {
                    "a": {"color": ["blue", "green"]},
                    "c": ANY,
                    "lu": ANY,
                }
            }
        }
    }

    change_set = msg["event"]["c"]["light.permitted"]
    additions = deepcopy(change_set["+"])
    _apply_entities_changes(state_dict, change_set)

    assert state_dict == {
        "attributes": {"effect": "help", "color": ["blue", "green"]},
        "context": {
            "id": additions["c"],
            "parent_id": None,
            "user_id": None,
        },
        "entity_id": "light.permitted",
        "last_changed": ANY,
        "last_updated": additions["lu"],
        "state": "on",
    }

    msg = await websocket_client.receive_json()
    assert msg["id"] == subscription
    assert msg["type"] == "event"
    assert msg["event"] == {"r": ["light.permitted"]}

    msg = await websocket_client.receive_json()
    assert msg["id"] == subscription
    assert msg["type"] == "event"
    assert msg["event"] == {
        "a": {
            "light.permitted": {
                "a": {"color": "blue", "effect": "help"},
                "c": ANY,
                "lc": ANY,
                "s": "on",
            }
        }
    }


async def test_subscribe_unsubscribe_entities_specific_entities(
    menuai: menuai,
    websocket_client: MockHAClientWebSocket,
    menuai_admin_user: MockUser,
) -> None:
    """Test subscribe/unsubscribe entities with a list of entity ids."""

    menuai.states.async_set("light.permitted", "off", {"color": "red"})
    menuai.states.async_set("light.not_intrested", "off", {"color": "blue"})
    original_state = menuai.states.get("light.permitted")
    assert isinstance(original_state, State)
    menuai_admin_user.groups = []
    menuai_admin_user.mock_policy(
        {
            "entities": {
                "entity_ids": {"light.permitted": True, "light.not_intrested": True}
            }
        }
    )

    await websocket_client.send_json_auto_id(
        {"type": "subscribe_entities", "entity_ids": ["light.permitted"]}
    )

    msg = await websocket_client.receive_json()
    subscription = msg["id"]
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]

    msg = await websocket_client.receive_json()
    assert msg["id"] == subscription
    assert msg["type"] == "event"
    assert isinstance(msg["event"]["a"]["light.permitted"]["c"], str)
    assert msg["event"] == {
        "a": {
            "light.permitted": {
                "a": {"color": "red"},
                "c": ANY,
                "lc": ANY,
                "s": "off",
            }
        }
    }
    menuai.states.async_set("light.not_intrested", "on", {"effect": "help"})
    menuai.states.async_set("light.not_permitted", "on")
    menuai.states.async_set("light.permitted", "on", {"color": "blue"})

    msg = await websocket_client.receive_json()
    assert msg["id"] == subscription
    assert msg["type"] == "event"
    assert msg["event"] == {
        "c": {
            "light.permitted": {
                "+": {
                    "a": {"color": "blue"},
                    "c": ANY,
                    "lc": ANY,
                    "s": "on",
                }
            }
        }
    }


async def test_subscribe_unsubscribe_entities_with_filter(
    menuai: menuai,
    websocket_client: MockHAClientWebSocket,
    menuai_admin_user: MockUser,
) -> None:
    """Test subscribe/unsubscribe entities with an entity filter."""
    menuai.states.async_set("switch.not_included", "off")
    menuai.states.async_set("light.include", "off")
    await websocket_client.send_json_auto_id(
        {"type": "subscribe_entities", "include": {"domains": ["light"]}}
    )

    msg = await websocket_client.receive_json()
    subscription = msg["id"]
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]

    msg = await websocket_client.receive_json()
    assert msg["id"] == subscription
    assert msg["type"] == "event"
    assert msg["event"] == {
        "a": {
            "light.include": {
                "a": {},
                "c": ANY,
                "lc": ANY,
                "s": "off",
            }
        }
    }
    menuai.states.async_set("switch.not_included", "on")
    menuai.states.async_set("light.include", "on")
    msg = await websocket_client.receive_json()
    assert msg["id"] == subscription
    assert msg["type"] == "event"
    assert msg["event"] == {
        "c": {
            "light.include": {
                "+": {
                    "c": ANY,
                    "lc": ANY,
                    "s": "on",
                }
            }
        }
    }


async def test_render_template_renders_template(
    menuai: menuai, websocket_client
) -> None:
    """Test simple template is rendered and updated."""
    menuai.states.async_set("light.test", "on")

    await websocket_client.send_json_auto_id(
        {
            "type": "render_template",
            "template": "State is: {{ states('light.test') }}",
        }
    )

    msg = await websocket_client.receive_json()
    subscription = msg["id"]
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]

    msg = await websocket_client.receive_json()
    assert msg["id"] == subscription
    assert msg["type"] == "event"
    event = msg["event"]
    assert event == {
        "result": "State is: on",
        "listeners": {
            "all": False,
            "domains": [],
            "entities": ["light.test"],
            "time": False,
        },
    }

    menuai.states.async_set("light.test", "off")
    msg = await websocket_client.receive_json()
    assert msg["id"] == subscription
    assert msg["type"] == "event"
    event = msg["event"]
    assert event == {
        "result": "State is: off",
        "listeners": {
            "all": False,
            "domains": [],
            "entities": ["light.test"],
            "time": False,
        },
    }


async def test_render_template_with_timeout_and_variables(
    menuai: menuai, websocket_client
) -> None:
    """Test a template with a timeout and variables renders without error."""
    await websocket_client.send_json_auto_id(
        {
            "type": "render_template",
            "timeout": 10,
            "variables": {"test": {"value": "hello"}},
            "template": "{{ test.value }}",
        }
    )

    msg = await websocket_client.receive_json()
    subscription = msg["id"]
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]

    msg = await websocket_client.receive_json()
    assert msg["id"] == subscription
    assert msg["type"] == "event"
    event = msg["event"]
    assert event == {
        "result": "hello",
        "listeners": {
            "all": False,
            "domains": [],
            "entities": [],
            "time": False,
        },
    }


async def test_render_template_manual_entity_ids_no_longer_needed(
    menuai: menuai, websocket_client
) -> None:
    """Test that updates to specified entity ids cause a template rerender."""
    menuai.states.async_set("light.test", "on")

    await websocket_client.send_json_auto_id(
        {
            "type": "render_template",
            "template": "State is: {{ states('light.test') }}",
        }
    )

    msg = await websocket_client.receive_json()
    subscription = msg["id"]
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]

    msg = await websocket_client.receive_json()
    assert msg["id"] == subscription
    assert msg["type"] == "event"
    event = msg["event"]
    assert event == {
        "result": "State is: on",
        "listeners": {
            "all": False,
            "domains": [],
            "entities": ["light.test"],
            "time": False,
        },
    }

    menuai.states.async_set("light.test", "off")
    msg = await websocket_client.receive_json()
    assert msg["id"] == subscription
    assert msg["type"] == "event"
    event = msg["event"]
    assert event == {
        "result": "State is: off",
        "listeners": {
            "all": False,
            "domains": [],
            "entities": ["light.test"],
            "time": False,
        },
    }


EMPTY_LISTENERS = {"all": False, "entities": [], "domains": [], "time": False}

ERR_MSG = {"type": "result", "success": False}

EVENT_UNDEFINED_FUNC_1 = {
    "error": "'my_unknown_func' is undefined",
    "level": "ERROR",
}
EVENT_UNDEFINED_FUNC_2 = {
    "error": "UndefinedError: 'my_unknown_func' is undefined",
    "level": "ERROR",
}

EVENT_UNDEFINED_VAR_WARN = {
    "error": "'my_unknown_var' is undefined",
    "level": "WARNING",
}
EVENT_UNDEFINED_VAR_ERR = {
    "error": "UndefinedError: 'my_unknown_var' is undefined",
    "level": "ERROR",
}

EVENT_UNDEFINED_FILTER = {
    "error": "TemplateAssertionError: No filter named 'unknown_filter'.",
    "level": "ERROR",
}


@pytest.mark.parametrize(
    ("template", "expected_events"),
    [
        (
            "{{ my_unknown_func() + 1 }}",
            [
                {"type": "event", "event": EVENT_UNDEFINED_FUNC_1},
                {"type": "event", "event": EVENT_UNDEFINED_FUNC_2},
                {"type": "result", "success": True, "result": None},
                {"type": "event", "event": EVENT_UNDEFINED_FUNC_1},
                {"type": "event", "event": EVENT_UNDEFINED_FUNC_2},
            ],
        ),
        (
            "{{ my_unknown_var }}",
            [
                {"type": "event", "event": EVENT_UNDEFINED_VAR_WARN},
                {"type": "result", "success": True, "result": None},
                {"type": "event", "event": EVENT_UNDEFINED_VAR_WARN},
                {
                    "type": "event",
                    "event": {"result": "", "listeners": EMPTY_LISTENERS},
                },
            ],
        ),
        (
            "{{ my_unknown_var + 1 }}",
            [
                {"type": "event", "event": EVENT_UNDEFINED_VAR_ERR},
                {"type": "result", "success": True, "result": None},
                {"type": "event", "event": EVENT_UNDEFINED_VAR_ERR},
            ],
        ),
        (
            "{{ now() | unknown_filter }}",
            [
                {"type": "event", "event": EVENT_UNDEFINED_FILTER},
                {"type": "result", "success": True, "result": None},
                {"type": "event", "event": EVENT_UNDEFINED_FILTER},
            ],
        ),
    ],
)
async def test_render_template_with_error(
    menuai: menuai,
    websocket_client: MockHAClientWebSocket,
    caplog: pytest.LogCaptureFixture,
    template: str,
    expected_events: list[dict[str, str]],
) -> None:
    """Test a template with an error."""
    caplog.set_level(logging.INFO)
    await websocket_client.send_json_auto_id(
        {
            "type": "render_template",
            "template": template,
            "report_errors": True,
        }
    )

    for expected_event in expected_events:
        msg = await websocket_client.receive_json()
        for key, value in expected_event.items():
            assert msg[key] == value

    assert "Template variable error" not in caplog.text
    assert "Template variable warning" not in caplog.text
    assert "TemplateError" not in caplog.text


@pytest.mark.parametrize(
    ("template", "expected_events"),
    [
        (
            "{{ my_unknown_func() + 1 }}",
            [
                {"type": "event", "event": EVENT_UNDEFINED_FUNC_1},
                {"type": "event", "event": EVENT_UNDEFINED_FUNC_2},
                {"type": "result", "success": True, "result": None},
                {"type": "event", "event": EVENT_UNDEFINED_FUNC_1},
                {"type": "event", "event": EVENT_UNDEFINED_FUNC_2},
                {"type": "event", "event": EVENT_UNDEFINED_FUNC_1},
            ],
        ),
        (
            "{{ my_unknown_var }}",
            [
                {"type": "event", "event": EVENT_UNDEFINED_VAR_WARN},
                {"type": "result", "success": True, "result": None},
                {"type": "event", "event": EVENT_UNDEFINED_VAR_WARN},
                {
                    "type": "event",
                    "event": {"result": "", "listeners": EMPTY_LISTENERS},
                },
            ],
        ),
        (
            "{{ my_unknown_var + 1 }}",
            [
                {"type": "event", "event": EVENT_UNDEFINED_VAR_ERR},
                {"type": "result", "success": True, "result": None},
                {"type": "event", "event": EVENT_UNDEFINED_VAR_ERR},
            ],
        ),
        (
            "{{ now() | unknown_filter }}",
            [
                {"type": "event", "event": EVENT_UNDEFINED_FILTER},
                {"type": "result", "success": True, "result": None},
                {"type": "event", "event": EVENT_UNDEFINED_FILTER},
            ],
        ),
    ],
)
async def test_render_template_with_timeout_and_error(
    menuai: menuai,
    websocket_client: MockHAClientWebSocket,
    caplog: pytest.LogCaptureFixture,
    template: str,
    expected_events: list[dict[str, str]],
) -> None:
    """Test a template with an error with a timeout."""
    caplog.set_level(logging.INFO)
    await websocket_client.send_json_auto_id(
        {
            "type": "render_template",
            "template": template,
            "timeout": 5,
            "report_errors": True,
        }
    )

    for expected_event in expected_events:
        msg = await websocket_client.receive_json()
        for key, value in expected_event.items():
            assert msg[key] == value

    assert "Template variable error" not in caplog.text
    assert "Template variable warning" not in caplog.text
    assert "TemplateError" not in caplog.text


@pytest.mark.parametrize(
    ("template", "expected_events"),
    [
        (
            "{{ my_unknown_func() + 1 }}",
            [
                {"type": "event", "event": EVENT_UNDEFINED_FUNC_2},
                {"type": "result", "success": True, "result": None},
                {"type": "event", "event": EVENT_UNDEFINED_FUNC_2},
            ],
        ),
        (
            "{{ my_unknown_var }}",
            [
                {"type": "event", "event": EVENT_UNDEFINED_VAR_ERR},
                {"type": "result", "success": True, "result": None},
                {"type": "event", "event": EVENT_UNDEFINED_VAR_ERR},
            ],
        ),
        (
            "{{ my_unknown_var + 1 }}",
            [
                {"type": "event", "event": EVENT_UNDEFINED_VAR_ERR},
                {"type": "result", "success": True, "result": None},
                {"type": "event", "event": EVENT_UNDEFINED_VAR_ERR},
            ],
        ),
        (
            "{{ now() | unknown_filter }}",
            [
                {"type": "event", "event": EVENT_UNDEFINED_FILTER},
                {"type": "result", "success": True, "result": None},
                {"type": "event", "event": EVENT_UNDEFINED_FILTER},
            ],
        ),
    ],
)
async def test_render_template_strict_with_timeout_and_error(
    menuai: menuai,
    websocket_client,
    caplog: pytest.LogCaptureFixture,
    template: str,
    expected_events: list[dict[str, str]],
) -> None:
    """Test a template with an error with a timeout.

    In this test report_errors is enabled.
    """
    caplog.set_level(logging.INFO)
    await websocket_client.send_json_auto_id(
        {
            "type": "render_template",
            "template": template,
            "timeout": 5,
            "strict": True,
            "report_errors": True,
        }
    )

    for expected_event in expected_events:
        msg = await websocket_client.receive_json()
        for key, value in expected_event.items():
            assert msg[key] == value

    assert "Template variable error" not in caplog.text
    assert "Template variable warning" not in caplog.text
    assert "TemplateError" not in caplog.text


@pytest.mark.parametrize(
    ("template", "expected_events"),
    [
        (
            "{{ my_unknown_func() + 1 }}",
            [
                {"type": "result", "success": True, "result": None},
            ],
        ),
        (
            "{{ my_unknown_var }}",
            [
                {"type": "result", "success": True, "result": None},
            ],
        ),
        (
            "{{ my_unknown_var + 1 }}",
            [
                {"type": "result", "success": True, "result": None},
            ],
        ),
        (
            "{{ now() | unknown_filter }}",
            [
                {"type": "result", "success": True, "result": None},
            ],
        ),
    ],
)
async def test_render_template_strict_with_timeout_and_error_2(
    menuai: menuai,
    websocket_client,
    caplog: pytest.LogCaptureFixture,
    template: str,
    expected_events: list[dict[str, str]],
) -> None:
    """Test a template with an error with a timeout.

    In this test report_errors is disabled.
    """
    caplog.set_level(logging.INFO)
    await websocket_client.send_json_auto_id(
        {
            "type": "render_template",
            "template": template,
            "timeout": 5,
            "strict": True,
        }
    )

    for expected_event in expected_events:
        msg = await websocket_client.receive_json()
        for key, value in expected_event.items():
            assert msg[key] == value

    assert "TemplateError" in caplog.text


@pytest.mark.parametrize(
    ("template", "expected_events_1", "expected_events_2"),
    [
        (
            "{{ now() | random }}",
            [
                {
                    "type": "event",
                    "event": {
                        "error": "TypeError: object of type 'datetime.datetime' has no len()",
                        "level": "ERROR",
                    },
                },
                {"type": "result", "success": True, "result": None},
                {
                    "type": "event",
                    "event": {
                        "error": "TypeError: object of type 'datetime.datetime' has no len()",
                        "level": "ERROR",
                    },
                },
            ],
            [],
        ),
        (
            "{{ float(states.sensor.foo.state) + 1 }}",
            [
                {
                    "type": "event",
                    "event": {
                        "error": "UndefinedError: 'None' has no attribute 'state'",
                        "level": "ERROR",
                    },
                },
                {"type": "result", "success": True, "result": None},
                {
                    "type": "event",
                    "event": {
                        "error": "UndefinedError: 'None' has no attribute 'state'",
                        "level": "ERROR",
                    },
                },
            ],
            [
                {
                    "type": "event",
                    "event": {
                        "result": 3.0,
                        "listeners": EMPTY_LISTENERS | {"entities": ["sensor.foo"]},
                    },
                },
            ],
        ),
    ],
)
async def test_render_template_error_in_template_code(
    menuai: menuai,
    websocket_client: MockHAClientWebSocket,
    caplog: pytest.LogCaptureFixture,
    template: str,
    expected_events_1: list[dict[str, str]],
    expected_events_2: list[dict[str, str]],
) -> None:
    """Test a template that will throw in template.py.

    In this test report_errors is enabled.
    """
    await websocket_client.send_json_auto_id(
        {
            "type": "render_template",
            "template": template,
            "report_errors": True,
        }
    )

    for expected_event in expected_events_1:
        msg = await websocket_client.receive_json()
        for key, value in expected_event.items():
            assert msg[key] == value

    menuai.states.async_set("sensor.foo", "2")

    for expected_event in expected_events_2:
        msg = await websocket_client.receive_json()
        for key, value in expected_event.items():
            assert msg[key] == value

    assert "Template variable error" not in caplog.text
    assert "Template variable warning" not in caplog.text
    assert "TemplateError" not in caplog.text


@pytest.mark.parametrize(
    ("template", "expected_events_1", "expected_events_2"),
    [
        (
            "{{ now() | random }}",
            [
                {"type": "result", "success": True, "result": None},
            ],
            [],
        ),
        (
            "{{ float(states.sensor.foo.state) + 1 }}",
            [
                {"type": "result", "success": True, "result": None},
            ],
            [
                {
                    "type": "event",
                    "event": {
                        "result": 3.0,
                        "listeners": EMPTY_LISTENERS | {"entities": ["sensor.foo"]},
                    },
                },
            ],
        ),
    ],
)
async def test_render_template_error_in_template_code_2(
    menuai: menuai,
    websocket_client,
    caplog: pytest.LogCaptureFixture,
    template: str,
    expected_events_1: list[dict[str, str]],
    expected_events_2: list[dict[str, str]],
) -> None:
    """Test a template that will throw in template.py.

    In this test report_errors is disabled.
    """
    await websocket_client.send_json_auto_id(
        {"type": "render_template", "template": template}
    )

    for expected_event in expected_events_1:
        msg = await websocket_client.receive_json()
        for key, value in expected_event.items():
            assert msg[key] == value

    menuai.states.async_set("sensor.foo", "2")

    for expected_event in expected_events_2:
        msg = await websocket_client.receive_json()
        for key, value in expected_event.items():
            assert msg[key] == value

    assert "TemplateError" in caplog.text


async def test_render_template_with_delayed_error(
    menuai: menuai,
    websocket_client: MockHAClientWebSocket,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test a template with an error that only happens after a state change.

    In this test report_errors is enabled.
    """
    caplog.set_level(logging.INFO)
    menuai.states.async_set("sensor.test", "on")
    await menuai.async_block_till_done()

    template_str = """
{% if states.sensor.test.state %}
   on
{% else %}
   {{ explode + 1 }}
{% endif %}
    """

    await websocket_client.send_json_auto_id(
        {
            "type": "render_template",
            "template": template_str,
            "report_errors": True,
        }
    )
    await menuai.async_block_till_done()

    msg = await websocket_client.receive_json()
    subscription = msg["id"]
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]

    menuai.states.async_remove("sensor.test")
    await menuai.async_block_till_done()

    msg = await websocket_client.receive_json()
    assert msg["id"] == subscription
    assert msg["type"] == "event"
    event = msg["event"]
    assert event == {
        "result": "on",
        "listeners": {
            "all": False,
            "domains": [],
            "entities": ["sensor.test"],
            "time": False,
        },
    }

    msg = await websocket_client.receive_json()
    assert msg["id"] == subscription
    assert msg["type"] == "event"
    event = msg["event"]
    assert event["error"] == "'None' has no attribute 'state'"

    msg = await websocket_client.receive_json()
    assert msg["id"] == subscription
    assert msg["type"] == "event"
    event = msg["event"]
    assert event == {
        "error": "UndefinedError: 'explode' is undefined",
        "level": "ERROR",
    }

    assert "Template variable error" not in caplog.text
    assert "Template variable warning" not in caplog.text
    assert "TemplateError" not in caplog.text


async def test_render_template_with_delayed_error_2(
    menuai: menuai, websocket_client, caplog: pytest.LogCaptureFixture
) -> None:
    """Test a template with an error that only happens after a state change.

    In this test report_errors is disabled.
    """
    menuai.states.async_set("sensor.test", "on")
    await menuai.async_block_till_done()

    template_str = """
{% if states.sensor.test.state %}
   on
{% else %}
   {{ explode + 1 }}
{% endif %}
    """

    await websocket_client.send_json_auto_id(
        {
            "type": "render_template",
            "template": template_str,
            "report_errors": False,
        }
    )
    await menuai.async_block_till_done()

    msg = await websocket_client.receive_json()
    subscription = msg["id"]
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]

    menuai.states.async_remove("sensor.test")
    await menuai.async_block_till_done()

    msg = await websocket_client.receive_json()
    assert msg["id"] == subscription
    assert msg["type"] == "event"
    event = msg["event"]
    assert event == {
        "result": "on",
        "listeners": {
            "all": False,
            "domains": [],
            "entities": ["sensor.test"],
            "time": False,
        },
    }

    assert "Template variable warning" in caplog.text


async def test_render_template_with_timeout(
    menuai: menuai,
    websocket_client: MockHAClientWebSocket,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test a template that will timeout."""

    slow_template_str = """
{% for var in range(1000) -%}
  {% for var in range(1000) -%}
    {{ var }}
  {%- endfor %}
{%- endfor %}
"""

    await websocket_client.send_json_auto_id(
        {
            "type": "render_template",
            "timeout": 0.000001,
            "template": slow_template_str,
        }
    )

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert not msg["success"]
    assert msg["error"]["code"] == const.ERR_TEMPLATE_ERROR

    assert "TemplateError" not in caplog.text


async def test_render_template_returns_with_match_all(
    menuai: menuai, websocket_client
) -> None:
    """Test that a template that would match with all entities still return success."""
    await websocket_client.send_json_auto_id(
        {"type": "render_template", "template": "State is: {{ 42 }}"}
    )

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]


async def test_manifest_list(
    menuai: menuai, websocket_client: MockHAClientWebSocket
) -> None:
    """Test loading manifests."""
    http = await async_get_integration(menuai, "http")
    websocket_api = await async_get_integration(menuai, "websocket_api")

    await websocket_client.send_json_auto_id({"type": "manifest/list"})

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]
    assert sorted(msg["result"], key=lambda manifest: manifest["domain"]) == [
        http.manifest,
        websocket_api.manifest,
    ]


async def test_manifest_list_specific_integrations(
    menuai: menuai, websocket_client
) -> None:
    """Test loading manifests for specific integrations."""
    websocket_api = await async_get_integration(menuai, "websocket_api")

    await websocket_client.send_json_auto_id(
        {"type": "manifest/list", "integrations": ["hue", "websocket_api"]}
    )
    hue = await async_get_integration(menuai, "hue")

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]
    assert sorted(msg["result"], key=lambda manifest: manifest["domain"]) == [
        hue.manifest,
        websocket_api.manifest,
    ]


async def test_manifest_get(
    menuai: menuai, websocket_client: MockHAClientWebSocket
) -> None:
    """Test getting a manifest."""
    hue = await async_get_integration(menuai, "hue")

    await websocket_client.send_json_auto_id(
        {"type": "manifest/get", "integration": "hue"}
    )

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]
    assert msg["result"] == hue.manifest

    # Non existing
    await websocket_client.send_json_auto_id(
        {"type": "manifest/get", "integration": "non_existing"}
    )

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert not msg["success"]
    assert msg["error"]["code"] == "not_found"


async def test_entity_source_admin(
    menuai: menuai,
    websocket_client: MockHAClientWebSocket,
    menuai_admin_user: MockUser,
) -> None:
    """Check that we fetch sources correctly."""
    platform = MockEntityPlatform(menuai)

    await platform.async_add_entities(
        [MockEntity(name="Entity 1"), MockEntity(name="Entity 2")]
    )

    # Fetch all
    await websocket_client.send_json_auto_id({"type": "entity/source"})

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]
    assert msg["result"] == {
        "test_domain.entity_1": {"domain": "test_platform"},
        "test_domain.entity_2": {"domain": "test_platform"},
    }

    # Mock policy
    menuai_admin_user.groups = []
    menuai_admin_user.mock_policy(
        {"entities": {"entity_ids": {"test_domain.entity_2": True}}}
    )

    # Fetch all
    await websocket_client.send_json_auto_id({"type": "entity/source"})

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]
    assert msg["result"] == {
        "test_domain.entity_2": {"domain": "test_platform"},
    }


async def test_subscribe_trigger(
    menuai: menuai, websocket_client: MockHAClientWebSocket
) -> None:
    """Test subscribing to a trigger."""
    init_count = sum(menuai.bus.async_listeners().values())

    await websocket_client.send_json_auto_id(
        {
            "type": "subscribe_trigger",
            "trigger": {"platform": "event", "event_type": "test_event"},
            "variables": {"hello": "world"},
        }
    )

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]

    # Verify we have a new listener
    assert sum(menuai.bus.async_listeners().values()) == init_count + 1

    context = Context()

    menuai.bus.async_fire("ignore_event")
    menuai.bus.async_fire("test_event", {"hello": "world"}, context=context)
    menuai.bus.async_fire("ignore_event")

    async with asyncio.timeout(3):
        msg = await websocket_client.receive_json()

    assert msg["type"] == "event"
    assert msg["event"]["context"]["id"] == context.id
    assert msg["event"]["variables"]["trigger"]["platform"] == "event"

    event = msg["event"]["variables"]["trigger"]["event"]

    assert event["event_type"] == "test_event"
    assert event["data"] == {"hello": "world"}
    assert event["origin"] == "LOCAL"

    await websocket_client.send_json_auto_id(
        {"type": "unsubscribe_events", "subscription": msg["id"]}
    )

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]

    # Check our listener got unsubscribed
    assert sum(menuai.bus.async_listeners().values()) == init_count


async def test_test_condition(
    menuai: menuai, websocket_client: MockHAClientWebSocket
) -> None:
    """Test testing a condition."""
    menuai.states.async_set("hello.world", "paulus")

    await websocket_client.send_json_auto_id(
        {
            "type": "test_condition",
            "condition": {
                "condition": "state",
                "entity_id": "hello.world",
                "state": "paulus",
            },
            "variables": {"hello": "world"},
        }
    )

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]
    assert msg["result"]["result"] is True

    await websocket_client.send_json_auto_id(
        {
            "type": "test_condition",
            "condition": {
                "condition": "template",
                "value_template": "{{ is_state('hello.world', 'paulus') }}",
            },
            "variables": {"hello": "world"},
        }
    )

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]
    assert msg["result"]["result"] is True

    await websocket_client.send_json_auto_id(
        {
            "type": "test_condition",
            "condition": {
                "condition": "template",
                "value_template": "{{ is_state('hello.world', 'frenck') }}",
            },
            "variables": {"hello": "world"},
        }
    )

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]
    assert msg["result"]["result"] is False


async def test_execute_script(
    menuai: menuai, websocket_client: MockHAClientWebSocket
) -> None:
    """Test testing a condition."""
    calls = async_mock_service(
        menuai, "domain_test", "test_service", response={"hello": "world"}
    )

    await websocket_client.send_json_auto_id(
        {
            "type": "execute_script",
            "sequence": [
                {
                    "service": "domain_test.test_service",
                    "data": {"hello": "world"},
                    "response_variable": "service_result",
                },
                {"stop": "done", "response_variable": "service_result"},
            ],
        }
    )

    msg_no_var = await websocket_client.receive_json()
    assert msg_no_var["type"] == const.TYPE_RESULT
    assert msg_no_var["success"]
    assert msg_no_var["result"]["response"] == {"hello": "world"}

    await websocket_client.send_json_auto_id(
        {
            "type": "execute_script",
            "sequence": {
                "service": "domain_test.test_service",
                "data": {"hello": "{{ name }}"},
            },
            "variables": {"name": "From variable"},
        }
    )

    msg_var = await websocket_client.receive_json()
    assert msg_var["type"] == const.TYPE_RESULT
    assert msg_var["success"]

    await menuai.async_block_till_done()
    await menuai.async_block_till_done()

    assert len(calls) == 2

    call = calls[0]
    assert call.domain == "domain_test"
    assert call.service == "test_service"
    assert call.data == {"hello": "world"}
    assert call.context.as_dict() == msg_no_var["result"]["context"]

    call = calls[1]
    assert call.domain == "domain_test"
    assert call.service == "test_service"
    assert call.data == {"hello": "From variable"}
    assert call.context.as_dict() == msg_var["result"]["context"]


@pytest.mark.parametrize(
    ("raise_exception", "err_code"),
    [
        (
            menuaiError(
                "Some error",
                translation_domain="test",
                translation_key="test_error",
                translation_placeholders={"option": "bla"},
            ),
            "home_assistant_error",
        ),
        (
            ServiceValidationError(
                "Some error",
                translation_domain="test",
                translation_key="test_error",
                translation_placeholders={"option": "bla"},
            ),
            "service_validation_error",
        ),
    ],
)
@pytest.mark.parametrize("ignore_translations_for_mock_domains", ["test"])
async def test_execute_script_err_localization(
    menuai: menuai,
    websocket_client: MockHAClientWebSocket,
    raise_exception: menuaiError,
    err_code: str,
) -> None:
    """Test testing a condition."""
    async_mock_service(
        menuai, "domain_test", "test_service", raise_exception=raise_exception
    )

    await websocket_client.send_json_auto_id(
        {
            "type": "execute_script",
            "sequence": [
                {
                    "service": "domain_test.test_service",
                    "data": {"hello": "world"},
                },
                {"stop": "done", "response_variable": "service_result"},
            ],
        }
    )

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"] is False
    assert msg["error"]["code"] == err_code
    assert msg["error"]["message"] == "Some error"
    assert msg["error"]["translation_key"] == "test_error"
    assert msg["error"]["translation_domain"] == "test"
    assert msg["error"]["translation_placeholders"] == {"option": "bla"}


async def test_execute_script_complex_response(
    menuai: menuai, menuai_ws_client: WebSocketGenerator
) -> None:
    """Test testing a condition."""
    await async_setup_component(menuai, "menuai", {})
    await async_setup_component(menuai, "calendar", {"calendar": {"platform": "demo"}})
    await menuai.async_block_till_done()
    ws_client = await menuai_ws_client(menuai)

    await ws_client.send_json_auto_id(
        {
            "type": "execute_script",
            "sequence": [
                {
                    "service": "calendar.get_events",
                    "data": {"duration": {"hours": 24, "minutes": 0, "seconds": 0}},
                    "target": {"entity_id": "calendar.calendar_1"},
                    "response_variable": "service_result",
                },
                {"stop": "done", "response_variable": "service_result"},
            ],
        }
    )

    msg_no_var = await ws_client.receive_json()
    assert msg_no_var["type"] == const.TYPE_RESULT
    assert msg_no_var["success"]
    assert msg_no_var["result"]["response"] == {
        "calendar.calendar_1": {
            "events": [
                {
                    "start": ANY,
                    "end": ANY,
                    "summary": "Future Event",
                    "description": "Future Description",
                    "location": "Future Location",
                }
            ]
        }
    }


async def test_execute_script_with_dynamically_validated_action(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    device_registry: dr.DeviceRegistry,
    fake_integration,
) -> None:
    """Test executing a script with an action which is dynamically validated."""

    ws_client = await menuai_ws_client(menuai)

    module_cache = menuai.data[loader.DATA_COMPONENTS]
    module = module_cache["fake_integration.device_action"]
    module.async_call_action_from_config = AsyncMock()
    module.async_validate_action_config = AsyncMock(
        side_effect=lambda menuai, config: config
    )

    config_entry = MockConfigEntry(domain="fake_integration", data={})
    config_entry.mock_state(menuai, ConfigEntryState.LOADED)
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )

    await ws_client.send_json_auto_id(
        {
            "type": "execute_script",
            "sequence": [
                {
                    "device_id": device_entry.id,
                    "domain": "fake_integration",
                },
            ],
        }
    )

    msg_no_var = await ws_client.receive_json()
    assert msg_no_var["type"] == const.TYPE_RESULT
    assert msg_no_var["success"]
    assert msg_no_var["result"]["response"] is None

    module.async_validate_action_config.assert_awaited_once()
    module.async_call_action_from_config.assert_awaited_once()


async def test_subscribe_unsubscribe_bootstrap_integrations(
    menuai: menuai,
    websocket_client: MockHAClientWebSocket,
    menuai_admin_user: MockUser,
) -> None:
    """Test subscribe/unsubscribe bootstrap_integrations."""
    await websocket_client.send_json_auto_id(
        {"type": "subscribe_bootstrap_integrations"}
    )

    msg = await websocket_client.receive_json()
    subscription = msg["id"]
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]

    message = {"august": 12.5, "isy994": 12.8}

    async_dispatcher_send(menuai, SIGNAL_BOOTSTRAP_INTEGRATIONS, message)
    msg = await websocket_client.receive_json()
    assert msg["id"] == subscription
    assert msg["type"] == "event"
    assert msg["event"] == message


async def test_integration_setup_info(
    menuai: menuai,
    websocket_client: MockHAClientWebSocket,
    menuai_admin_user: MockUser,
) -> None:
    """Test subscribe/unsubscribe bootstrap_integrations."""
    with patch(
        "menuai.components.websocket_api.commands.async_get_setup_timings",
        return_value={
            "august": 12.5,
            "isy994": 12.8,
        },
    ):
        await websocket_client.send_json_auto_id({"type": "integration/setup_info"})
        msg = await websocket_client.receive_json()

    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]
    assert msg["result"] == [
        {"domain": "august", "seconds": 12.5},
        {"domain": "isy994", "seconds": 12.8},
    ]


@pytest.mark.parametrize(
    ("key", "config"),
    [
        ("triggers", {"platform": "event", "event_type": "hello"}),
        ("triggers", [{"platform": "event", "event_type": "hello"}]),
        (
            "conditions",
            {"condition": "state", "entity_id": "hello.world", "state": "paulus"},
        ),
        (
            "conditions",
            [{"condition": "state", "entity_id": "hello.world", "state": "paulus"}],
        ),
        ("actions", {"service": "domain_test.test_service"}),
        ("actions", [{"service": "domain_test.test_service"}]),
    ],
)
async def test_validate_config_works(
    websocket_client: MockHAClientWebSocket,
    key: str,
    config: dict[str, Any] | list[dict[str, Any]],
) -> None:
    """Test config validation."""
    await websocket_client.send_json_auto_id({"type": "validate_config", key: config})

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]
    assert msg["result"] == {key: {"valid": True, "error": None}}


@pytest.mark.parametrize(
    ("key", "config", "error"),
    [
        # Raises vol.Invalid
        (
            "triggers",
            {"platform": "non_existing", "event_type": "hello"},
            "Invalid trigger 'non_existing' specified",
        ),
        # Raises vol.Invalid
        (
            "conditions",
            {
                "condition": "non_existing",
                "entity_id": "hello.world",
                "state": "paulus",
            },
            (
                "Invalid condition \"non_existing\" specified {'condition': "
                "'non_existing', 'entity_id': 'hello.world', 'state': 'paulus'}"
            ),
        ),
        # Raises menuaiError
        (
            "conditions",
            {
                "above": 50,
                "condition": "device",
                "device_id": "a51a57e5af051eb403d56eb9e6fd691c",
                "domain": "sensor",
                "entity_id": "7d18a157b7c00adbf2982ea7de0d0362",
                "type": "is_carbon_dioxide",
            },
            "Unknown device 'a51a57e5af051eb403d56eb9e6fd691c'",
        ),
        # Raises vol.Invalid
        (
            "actions",
            {"non_existing": "domain_test.test_service"},
            "Unable to determine action @ data[0]",
        ),
    ],
)
async def test_validate_config_invalid(
    websocket_client: MockHAClientWebSocket,
    key: str,
    config: dict[str, Any],
    error: str,
) -> None:
    """Test config validation."""
    await websocket_client.send_json_auto_id({"type": "validate_config", key: config})

    msg = await websocket_client.receive_json()
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]
    assert msg["result"] == {key: {"valid": False, "error": error}}


async def test_message_coalescing(
    menuai: menuai,
    websocket_client: MockHAClientWebSocket,
    menuai_admin_user: MockUser,
) -> None:
    """Test enabling message coalescing."""
    await websocket_client.send_json(
        {
            "id": 1,
            "type": "supported_features",
            "features": {FEATURE_COALESCE_MESSAGES: 1},
        }
    )
    menuai.states.async_set("light.permitted", "on", {"color": "red"})

    data = await websocket_client.receive_str()
    msg = json_loads(data)
    assert msg["id"] == 1
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]

    await websocket_client.send_json({"id": 7, "type": "subscribe_entities"})

    data = await websocket_client.receive_str()
    msgs = json_loads(data)
    msg = msgs.pop(0)
    assert msg["id"] == 7
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]

    msg = msgs.pop(0)
    assert msg["id"] == 7
    assert msg["type"] == "event"
    assert msg["event"] == {
        "a": {
            "light.permitted": {"a": {"color": "red"}, "c": ANY, "lc": ANY, "s": "on"}
        }
    }

    menuai.states.async_set("light.permitted", "on", {"color": "yellow"})
    menuai.states.async_set("light.permitted", "on", {"color": "green"})
    menuai.states.async_set("light.permitted", "on", {"color": "blue"})

    data = await websocket_client.receive_str()
    msgs = json_loads(data)

    msg = msgs.pop(0)
    assert msg["id"] == 7
    assert msg["type"] == "event"
    assert msg["event"] == {
        "c": {"light.permitted": {"+": {"a": {"color": "yellow"}, "c": ANY, "lu": ANY}}}
    }

    msg = msgs.pop(0)
    assert msg["id"] == 7
    assert msg["type"] == "event"
    assert msg["event"] == {
        "c": {"light.permitted": {"+": {"a": {"color": "green"}, "c": ANY, "lu": ANY}}}
    }

    msg = msgs.pop(0)
    assert msg["id"] == 7
    assert msg["type"] == "event"
    assert msg["event"] == {
        "c": {"light.permitted": {"+": {"a": {"color": "blue"}, "c": ANY, "lu": ANY}}}
    }

    menuai.states.async_set("light.permitted", "on", {"color": "yellow"})
    menuai.states.async_set("light.permitted", "on", {"color": "green"})
    menuai.states.async_set("light.permitted", "on", {"color": "blue"})
    await websocket_client.close()
    await menuai.async_block_till_done()


async def test_message_coalescing_not_supported_by_websocket_client(
    menuai: menuai,
    websocket_client: MockHAClientWebSocket,
    menuai_admin_user: MockUser,
) -> None:
    """Test enabling message coalescing not supported by websocket client."""
    await websocket_client.send_json({"id": 7, "type": "subscribe_entities"})

    data = await websocket_client.receive_str()
    msg = json_loads(data)
    assert msg["id"] == 7
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]

    menuai.states.async_set("light.permitted", "on", {"color": "red"})
    menuai.states.async_set("light.permitted", "on", {"color": "blue"})

    data = await websocket_client.receive_str()
    msg = json_loads(data)
    assert msg["id"] == 7
    assert msg["type"] == "event"
    assert msg["event"] == {"a": {}}

    data = await websocket_client.receive_str()
    msg = json_loads(data)
    assert msg["id"] == 7
    assert msg["type"] == "event"
    assert msg["event"] == {
        "a": {
            "light.permitted": {"a": {"color": "red"}, "c": ANY, "lc": ANY, "s": "on"}
        }
    }

    data = await websocket_client.receive_str()
    msg = json_loads(data)
    assert msg["id"] == 7
    assert msg["type"] == "event"
    assert msg["event"] == {
        "c": {"light.permitted": {"+": {"a": {"color": "blue"}, "c": ANY, "lu": ANY}}}
    }
    await websocket_client.close()
    await menuai.async_block_till_done()


async def test_client_message_coalescing(
    menuai: menuai,
    websocket_client: MockHAClientWebSocket,
    menuai_admin_user: MockUser,
) -> None:
    """Test client message coalescing."""
    await websocket_client.send_json(
        [
            {
                "id": 1,
                "type": "supported_features",
                "features": {FEATURE_COALESCE_MESSAGES: 1},
            },
            {"id": 7, "type": "subscribe_entities"},
        ]
    )
    menuai.states.async_set("light.permitted", "on", {"color": "red"})

    data = await websocket_client.receive_str()
    msgs = json_loads(data)

    msg = msgs.pop(0)
    assert msg["id"] == 1
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]

    msg = msgs.pop(0)
    assert msg["id"] == 7
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]

    msg = msgs.pop(0)
    assert msg["id"] == 7
    assert msg["type"] == "event"
    assert msg["event"] == {
        "a": {
            "light.permitted": {"a": {"color": "red"}, "c": ANY, "lc": ANY, "s": "on"}
        }
    }

    menuai.states.async_set("light.permitted", "on", {"color": "yellow"})
    menuai.states.async_set("light.permitted", "on", {"color": "green"})
    menuai.states.async_set("light.permitted", "on", {"color": "blue"})

    data = await websocket_client.receive_str()
    msgs = json_loads(data)

    msg = msgs.pop(0)
    assert msg["id"] == 7
    assert msg["type"] == "event"
    assert msg["event"] == {
        "c": {"light.permitted": {"+": {"a": {"color": "yellow"}, "c": ANY, "lu": ANY}}}
    }

    msg = msgs.pop(0)
    assert msg["id"] == 7
    assert msg["type"] == "event"
    assert msg["event"] == {
        "c": {"light.permitted": {"+": {"a": {"color": "green"}, "c": ANY, "lu": ANY}}}
    }

    msg = msgs.pop(0)
    assert msg["id"] == 7
    assert msg["type"] == "event"
    assert msg["event"] == {
        "c": {"light.permitted": {"+": {"a": {"color": "blue"}, "c": ANY, "lu": ANY}}}
    }

    menuai.states.async_set("light.permitted", "on", {"color": "yellow"})
    menuai.states.async_set("light.permitted", "on", {"color": "green"})
    menuai.states.async_set("light.permitted", "on", {"color": "blue"})
    await websocket_client.close()
    await menuai.async_block_till_done()


async def test_integration_descriptions(
    menuai: menuai, menuai_ws_client: WebSocketGenerator
) -> None:
    """Test we can get integration descriptions."""
    assert await async_setup_component(menuai, "config", {})
    ws_client = await menuai_ws_client(menuai)

    await ws_client.send_json_auto_id({"type": "integration/descriptions"})
    response = await ws_client.receive_json()

    assert response["success"]
    assert response["result"]


async def test_subscribe_entities_chained_state_change(
    menuai: menuai,
    websocket_client: MockHAClientWebSocket,
    menuai_admin_user: MockUser,
) -> None:
    """Test chaining state changed events.

    Ensure the websocket sends the off state after
    the on state.
    """

    @callback
    def auto_off_listener(event):
        menuai.states.async_set("light.permitted", "off")

    async_track_state_change_event(menuai, ["light.permitted"], auto_off_listener)

    await websocket_client.send_json_auto_id({"type": "subscribe_entities"})

    data = await websocket_client.receive_str()
    msg = json_loads(data)
    subscription = msg["id"]
    assert msg["type"] == const.TYPE_RESULT
    assert msg["success"]

    data = await websocket_client.receive_str()
    msg = json_loads(data)
    assert msg["id"] == subscription
    assert msg["type"] == "event"
    assert msg["event"] == {"a": {}}

    menuai.states.async_set("light.permitted", "on")
    data = await websocket_client.receive_str()
    msg = json_loads(data)
    assert msg["id"] == subscription
    assert msg["type"] == "event"
    assert msg["event"] == {
        "a": {"light.permitted": {"a": {}, "c": ANY, "lc": ANY, "s": "on"}}
    }
    data = await websocket_client.receive_str()
    msg = json_loads(data)
    assert msg["id"] == subscription
    assert msg["type"] == "event"
    assert msg["event"] == {
        "c": {"light.permitted": {"+": {"c": ANY, "lc": ANY, "s": "off"}}}
    }

    await websocket_client.close()
    await menuai.async_block_till_done()


@pytest.mark.parametrize(
    ("domain", "result"),
    [
        ("config", {"integration_loaded": True}),
        ("non_existing_domain", {"integration_loaded": False}),
    ],
)
async def test_wait_integration(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    domain: str,
    result: dict[str, Any],
) -> None:
    """Test we can get wait for an integration to load."""
    assert await async_setup_component(menuai, "config", {})
    ws_client = await menuai_ws_client(menuai)

    await ws_client.send_json_auto_id({"type": "integration/wait", "domain": domain})
    response = await ws_client.receive_json()
    assert response == {
        "id": ANY,
        "result": result,
        "success": True,
        "type": "result",
    }


async def test_wait_integration_startup(
    menuai: menuai, menuai_ws_client: WebSocketGenerator
) -> None:
    """Test we can get wait for an integration to load during startup."""
    ws_client = await menuai_ws_client(menuai)

    setup_stall = asyncio.Event()
    setup_started = asyncio.Event()

    async def mock_setup(menuai: menuai, _) -> bool:
        setup_started.set()
        await setup_stall.wait()
        return True

    mock_integration(menuai, MockModule("test", async_setup=mock_setup))

    # The integration is not loaded, and is also not scheduled to load
    await ws_client.send_json_auto_id({"type": "integration/wait", "domain": "test"})
    response = await ws_client.receive_json()
    assert response == {
        "id": ANY,
        "result": {"integration_loaded": False},
        "success": True,
        "type": "result",
    }

    # Mark the component as scheduled to be loaded
    async_set_domains_to_be_loaded(menuai, {"test"})

    # Start loading the component, including its config entries
    menuai.async_create_task(async_setup_component(menuai, "test", {}))
    await setup_started.wait()

    # The component is not yet loaded
    assert "test" not in menuai.config.components

    # Allow setup to proceed
    setup_stall.set()

    # The component is scheduled to load, this will block until the config entry is loaded
    await ws_client.send_json_auto_id({"type": "integration/wait", "domain": "test"})
    response = await ws_client.receive_json()
    assert response == {
        "id": ANY,
        "result": {"integration_loaded": True},
        "success": True,
        "type": "result",
    }

    # The component has been loaded
    assert "test" in menuai.config.components
