"""The tests for the MenuAI API component."""

import asyncio
from http import HTTPStatus
import json
from typing import Any
from unittest.mock import patch

from aiohttp import ServerDisconnectedError, web
from aiohttp.test_utils import TestClient
import pytest
import voluptuous as vol

from menuai import const, core as ha
from menuai.auth.models import Credentials
from menuai.bootstrap import DATA_LOGGING
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import CLIENT_ID, MockUser, async_mock_service
from tests.typing import ClientSessionGenerator


@pytest.fixture
async def mock_api_client(
    menuai: menuai, menuai_client: ClientSessionGenerator
) -> TestClient:
    """Start the MenuAI HTTP component and return admin API client."""
    await async_setup_component(menuai, "api", {})
    return await menuai_client()


async def test_api_list_state_entities(
    menuai: menuai, mock_api_client: TestClient
) -> None:
    """Test if the debug interface allows us to list state entities."""
    menuai.states.async_set("test.entity", "hello")
    resp = await mock_api_client.get(const.URL_API_STATES)
    assert resp.status == HTTPStatus.OK
    json = await resp.json()

    remote_data = [ha.State.from_dict(item).as_dict() for item in json]
    local_data = [state.as_dict() for state in menuai.states.async_all()]
    assert remote_data == local_data


async def test_api_get_state(menuai: menuai, mock_api_client: TestClient) -> None:
    """Test if the debug interface allows us to get a state."""
    menuai.states.async_set("hello.world", "nice", {"attr": 1})
    resp = await mock_api_client.get("/api/states/hello.world")
    assert resp.status == HTTPStatus.OK
    json = await resp.json()

    data = ha.State.from_dict(json)

    state = menuai.states.get("hello.world")

    assert data.state == state.state
    assert data.last_changed == state.last_changed
    assert data.attributes == state.attributes


async def test_api_get_non_existing_state(
    menuai: menuai, mock_api_client: TestClient
) -> None:
    """Test if the debug interface allows us to get a state."""
    resp = await mock_api_client.get("/api/states/does_not_exist")
    assert resp.status == HTTPStatus.NOT_FOUND


async def test_api_state_change(
    menuai: menuai, mock_api_client: TestClient
) -> None:
    """Test if we can change the state of an entity that exists."""
    menuai.states.async_set("test.test", "not_to_be_set")

    await mock_api_client.post(
        "/api/states/test.test", json={"state": "debug_state_change2"}
    )

    assert menuai.states.get("test.test").state == "debug_state_change2"


async def test_api_state_change_of_non_existing_entity(
    menuai: menuai, mock_api_client: TestClient
) -> None:
    """Test if changing a state of a non existing entity is possible."""
    new_state = "debug_state_change"

    resp = await mock_api_client.post(
        "/api/states/test_entity.that_does_not_exist", json={"state": new_state}
    )

    assert resp.status == HTTPStatus.CREATED

    assert menuai.states.get("test_entity.that_does_not_exist").state == new_state


async def test_api_state_change_with_bad_entity_id(
    menuai: menuai, mock_api_client: TestClient
) -> None:
    """Test if API sends appropriate error if we omit state."""
    resp = await mock_api_client.post(
        "/api/states/bad.entity.id", json={"state": "new_state"}
    )

    assert resp.status == HTTPStatus.BAD_REQUEST


async def test_api_state_change_with_bad_state(
    menuai: menuai, mock_api_client: TestClient
) -> None:
    """Test if API sends appropriate error if we omit state."""
    resp = await mock_api_client.post(
        "/api/states/test.test", json={"state": "x" * 256}
    )

    assert resp.status == HTTPStatus.BAD_REQUEST


async def test_api_state_change_with_bad_data(
    menuai: menuai, mock_api_client: TestClient
) -> None:
    """Test if API sends appropriate error if we omit state."""
    resp = await mock_api_client.post(
        "/api/states/test_entity.that_does_not_exist", json={}
    )

    assert resp.status == HTTPStatus.BAD_REQUEST


async def test_api_state_change_to_zero_value(
    menuai: menuai, mock_api_client: TestClient
) -> None:
    """Test if changing a state to a zero value is possible."""
    resp = await mock_api_client.post(
        "/api/states/test_entity.with_zero_state", json={"state": 0}
    )

    assert resp.status == HTTPStatus.CREATED

    resp = await mock_api_client.post(
        "/api/states/test_entity.with_zero_state", json={"state": 0.0}
    )

    assert resp.status == HTTPStatus.OK


async def test_api_state_change_push(
    menuai: menuai, mock_api_client: TestClient
) -> None:
    """Test if we can push a change the state of an entity."""
    menuai.states.async_set("test.test", "not_to_be_set")

    events = []

    @ha.callback
    def event_listener(event):
        """Track events."""
        events.append(event)

    menuai.bus.async_listen(const.EVENT_STATE_CHANGED, event_listener)

    await mock_api_client.post("/api/states/test.test", json={"state": "not_to_be_set"})
    await menuai.async_block_till_done()
    assert len(events) == 0

    await mock_api_client.post(
        "/api/states/test.test", json={"state": "not_to_be_set", "force_update": True}
    )
    await menuai.async_block_till_done()
    assert len(events) == 1


async def test_api_fire_event_with_no_data(
    menuai: menuai, mock_api_client: TestClient
) -> None:
    """Test if the API allows us to fire an event."""
    test_value = []

    @ha.callback
    def listener(event):
        """Record that our event got called."""
        test_value.append(1)

    menuai.bus.async_listen_once("test.event_no_data", listener)

    await mock_api_client.post("/api/events/test.event_no_data")
    await menuai.async_block_till_done()

    assert len(test_value) == 1


async def test_api_fire_event_with_data(
    menuai: menuai, mock_api_client: TestClient
) -> None:
    """Test if the API allows us to fire an event."""
    test_value = []

    @ha.callback
    def listener(event):
        """Record that our event got called.

        Also test if our data came through.
        """
        if "test" in event.data:
            test_value.append(1)

    menuai.bus.async_listen_once("test_event_with_data", listener)

    await mock_api_client.post("/api/events/test_event_with_data", json={"test": 1})

    await menuai.async_block_till_done()

    assert len(test_value) == 1


async def test_api_fire_event_with_invalid_json(
    menuai: menuai, mock_api_client: TestClient
) -> None:
    """Test if the API allows us to fire an event."""
    test_value = []

    @ha.callback
    def listener(event):
        """Record that our event got called."""
        test_value.append(1)

    menuai.bus.async_listen_once("test_event_bad_data", listener)

    resp = await mock_api_client.post(
        "/api/events/test_event_bad_data", data=json.dumps("not an object")
    )

    await menuai.async_block_till_done()

    assert resp.status == HTTPStatus.BAD_REQUEST
    assert len(test_value) == 0

    # Try now with valid but unusable JSON
    resp = await mock_api_client.post(
        "/api/events/test_event_bad_data", data=json.dumps([1, 2, 3])
    )

    await menuai.async_block_till_done()

    assert resp.status == HTTPStatus.BAD_REQUEST
    assert len(test_value) == 0


async def test_api_get_config(menuai: menuai, mock_api_client: TestClient) -> None:
    """Test the return of the configuration."""
    resp = await mock_api_client.get(const.URL_API_CONFIG)
    result = await resp.json()
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


async def test_api_get_components(
    menuai: menuai, mock_api_client: TestClient
) -> None:
    """Test the return of the components."""
    resp = await mock_api_client.get(const.URL_API_COMPONENTS)
    result = await resp.json()
    assert set(result) == menuai.config.components


async def test_api_get_event_listeners(
    menuai: menuai, mock_api_client: TestClient
) -> None:
    """Test if we can get the list of events being listened for."""
    resp = await mock_api_client.get(const.URL_API_EVENTS)
    data = await resp.json()

    local = menuai.bus.async_listeners()

    for event in data:
        assert local.pop(event["event"]) == event["listener_count"]

    assert len(local) == 0


async def test_api_get_services(
    menuai: menuai, mock_api_client: TestClient
) -> None:
    """Test if we can get a dict describing current services."""
    resp = await mock_api_client.get(const.URL_API_SERVICES)
    data = await resp.json()
    local_services = menuai.services.async_services()

    for serv_domain in data:
        local = local_services.pop(serv_domain["domain"])

        assert serv_domain["services"].keys() == local.keys()


async def test_api_call_service_no_data(
    menuai: menuai, mock_api_client: TestClient
) -> None:
    """Test if the API allows us to call a service."""
    test_value = []

    @ha.callback
    def listener(service_call):
        """Record that our service got called."""
        test_value.append(1)

    menuai.services.async_register("test_domain", "test_service", listener)

    await mock_api_client.post("/api/services/test_domain/test_service")
    await menuai.async_block_till_done()
    assert len(test_value) == 1


async def test_api_call_service_with_data(
    menuai: menuai, mock_api_client: TestClient
) -> None:
    """Test if the API allows us to call a service."""

    @ha.callback
    def listener(service_call):
        """Record that our service got called.

        Also test if our data came through.
        """
        menuai.states.async_set(
            "test.data",
            "on",
            {"data": service_call.data["test"]},
            context=service_call.context,
        )

    menuai.services.async_register("test_domain", "test_service", listener)

    resp = await mock_api_client.post(
        "/api/services/test_domain/test_service", json={"test": 1}
    )
    data = await resp.json()
    assert len(data) == 1
    state = data[0]
    assert state["entity_id"] == "test.data"
    assert state["state"] == "on"
    assert state["attributes"] == {"data": 1}


SERVICE_DICT = {"changed_states": [], "service_response": {"foo": "bar"}}
RESP_REQUIRED = {
    "message": (
        "Service call requires responses but caller did not ask for "
        "responses. Add ?return_response to query parameters."
    )
}
RESP_UNSUPPORTED = {
    "message": "Service does not support responses. Remove return_response from request."
}


@pytest.mark.parametrize(
    (
        "supports_response",
        "requested_response",
        "expected_number_of_service_calls",
        "expected_status",
        "expected_response",
    ),
    [
        (ha.SupportsResponse.ONLY, True, 1, HTTPStatus.OK, SERVICE_DICT),
        (ha.SupportsResponse.ONLY, False, 0, HTTPStatus.BAD_REQUEST, RESP_REQUIRED),
        (ha.SupportsResponse.OPTIONAL, True, 1, HTTPStatus.OK, SERVICE_DICT),
        (ha.SupportsResponse.OPTIONAL, False, 1, HTTPStatus.OK, []),
        (ha.SupportsResponse.NONE, True, 0, HTTPStatus.BAD_REQUEST, RESP_UNSUPPORTED),
        (ha.SupportsResponse.NONE, False, 1, HTTPStatus.OK, []),
    ],
)
async def test_api_call_service_returns_response_requested_response(
    menuai: menuai,
    mock_api_client: TestClient,
    supports_response: ha.SupportsResponse,
    requested_response: bool,
    expected_number_of_service_calls: int,
    expected_status: int,
    expected_response: Any,
) -> None:
    """Test if the API allows us to call a service."""
    test_value = []

    @ha.callback
    def listener(service_call):
        """Record that our service got called."""
        test_value.append(1)
        return {"foo": "bar"}

    menuai.services.async_register(
        "test_domain", "test_service", listener, supports_response=supports_response
    )

    resp = await mock_api_client.post(
        "/api/services/test_domain/test_service"
        + ("?return_response" if requested_response else "")
    )
    assert resp.status == expected_status
    await menuai.async_block_till_done()
    assert len(test_value) == expected_number_of_service_calls
    assert await resp.json() == expected_response


async def test_api_call_service_client_closed(
    menuai: menuai, mock_api_client: TestClient
) -> None:
    """Test that services keep running if client is closed."""
    test_value = []

    fut = menuai.loop.create_future()
    service_call_started = asyncio.Event()

    async def listener(service_call):
        """Wait and return after mock_api_client.post finishes."""
        service_call_started.set()
        value = await fut
        test_value.append(value)

    menuai.services.async_register("test_domain", "test_service", listener)

    api_task = menuai.async_create_task(
        mock_api_client.post("/api/services/test_domain/test_service")
    )

    await service_call_started.wait()

    assert len(test_value) == 0

    await mock_api_client.close()

    assert len(test_value) == 0
    assert api_task.done()

    with pytest.raises(ServerDisconnectedError):
        await api_task

    fut.set_result(1)
    await menuai.async_block_till_done()

    assert len(test_value) == 1
    assert test_value[0] == 1


async def test_api_template(menuai: menuai, mock_api_client: TestClient) -> None:
    """Test the template API."""
    menuai.states.async_set("sensor.temperature", 10)

    resp = await mock_api_client.post(
        const.URL_API_TEMPLATE,
        json={"template": "{{ states.sensor.temperature.state }}"},
    )

    body = await resp.text()

    assert body == "10"

    menuai.states.async_set("sensor.temperature", 20)
    resp = await mock_api_client.post(
        const.URL_API_TEMPLATE,
        json={"template": "{{ states.sensor.temperature.state }}"},
    )

    body = await resp.text()

    assert body == "20"

    menuai.states.async_remove("sensor.temperature")
    resp = await mock_api_client.post(
        const.URL_API_TEMPLATE,
        json={"template": "{{ states.sensor.temperature.state }}"},
    )

    body = await resp.text()

    assert body == ""


async def test_api_template_cached(
    menuai: menuai, mock_api_client: TestClient
) -> None:
    """Test the template API uses the cache."""
    menuai.states.async_set("sensor.temperature", 30)

    resp = await mock_api_client.post(
        const.URL_API_TEMPLATE,
        json={"template": "{{ states.sensor.temperature.state }}"},
    )

    body = await resp.text()

    assert body == "30"

    menuai.states.async_set("sensor.temperature", 40)
    resp = await mock_api_client.post(
        const.URL_API_TEMPLATE,
        json={"template": "{{ states.sensor.temperature.state }}"},
    )

    body = await resp.text()

    assert body == "40"


async def test_api_template_error(
    menuai: menuai, mock_api_client: TestClient
) -> None:
    """Test the template API."""
    menuai.states.async_set("sensor.temperature", 10)

    resp = await mock_api_client.post(
        const.URL_API_TEMPLATE, json={"template": "{{ states.sensor.temperature.state"}
    )

    assert resp.status == HTTPStatus.BAD_REQUEST


async def test_stream(menuai: menuai, mock_api_client: TestClient) -> None:
    """Test the stream."""
    listen_count = _listen_count(menuai)

    async with mock_api_client.get(const.URL_API_STREAM) as resp:
        assert resp.status == HTTPStatus.OK
        assert listen_count + 1 == _listen_count(menuai)

        menuai.bus.async_fire("test_event")

        data = await _stream_next_event(resp.content)

        assert data["event_type"] == "test_event"


async def test_stream_with_restricted(
    menuai: menuai, mock_api_client: TestClient
) -> None:
    """Test the stream with restrictions."""
    listen_count = _listen_count(menuai)

    async with mock_api_client.get(
        f"{const.URL_API_STREAM}?restrict=test_event1,test_event3"
    ) as resp:
        assert resp.status == HTTPStatus.OK
        assert listen_count + 1 == _listen_count(menuai)

        menuai.bus.async_fire("test_event1")
        data = await _stream_next_event(resp.content)
        assert data["event_type"] == "test_event1"

        menuai.bus.async_fire("test_event2")
        menuai.bus.async_fire("test_event3")
        data = await _stream_next_event(resp.content)
        assert data["event_type"] == "test_event3"


async def _stream_next_event(stream):
    """Read the stream for next event while ignoring ping."""
    while True:
        last_new_line = False
        data = b""

        while True:
            dat = await stream.read(1)
            if dat == b"\n" and last_new_line:
                break
            data += dat
            last_new_line = dat == b"\n"

        conv = data.decode("utf-8").strip()[6:]

        if conv != "ping":
            break
    return json.loads(conv)


def _listen_count(menuai: menuai) -> int:
    """Return number of event listeners."""
    return sum(menuai.bus.async_listeners().values())


async def test_api_error_log(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    menuai_access_token: str,
    menuai_admin_user: MockUser,
) -> None:
    """Test if we can fetch the error log."""
    menuai.data[DATA_LOGGING] = "/some/path"
    await async_setup_component(menuai, "api", {})
    client = await menuai_client_no_auth()

    resp = await client.get(const.URL_API_ERROR_LOG)
    # Verify auth required
    assert resp.status == HTTPStatus.UNAUTHORIZED

    with patch(
        "aiohttp.web.FileResponse", return_value=web.Response(text="Hello")
    ) as mock_file:
        resp = await client.get(
            const.URL_API_ERROR_LOG,
            headers={"Authorization": f"Bearer {menuai_access_token}"},
        )

    assert len(mock_file.mock_calls) == 1
    assert mock_file.mock_calls[0][1][0] == menuai.data[DATA_LOGGING]
    assert resp.status == HTTPStatus.OK
    assert await resp.text() == "Hello"

    # Verify we require admin user
    menuai_admin_user.groups = []
    resp = await client.get(
        const.URL_API_ERROR_LOG,
        headers={"Authorization": f"Bearer {menuai_access_token}"},
    )
    assert resp.status == HTTPStatus.UNAUTHORIZED


async def test_api_fire_event_context(
    menuai: menuai, mock_api_client: TestClient, menuai_access_token: str
) -> None:
    """Test if the API sets right context if we fire an event."""
    test_value = []

    @ha.callback
    def listener(event):
        """Record that our event got called."""
        test_value.append(event)

    menuai.bus.async_listen("test.event", listener)

    await mock_api_client.post(
        "/api/events/test.event",
        headers={"authorization": f"Bearer {menuai_access_token}"},
    )
    await menuai.async_block_till_done()

    refresh_token = menuai.auth.async_validate_access_token(menuai_access_token)

    assert len(test_value) == 1
    assert test_value[0].context.user_id == refresh_token.user.id


async def test_api_call_service_context(
    menuai: menuai, mock_api_client: TestClient, menuai_access_token: str
) -> None:
    """Test if the API sets right context if we call a service."""
    calls = async_mock_service(menuai, "test_domain", "test_service")

    await mock_api_client.post(
        "/api/services/test_domain/test_service",
        headers={"authorization": f"Bearer {menuai_access_token}"},
    )
    await menuai.async_block_till_done()

    refresh_token = menuai.auth.async_validate_access_token(menuai_access_token)

    assert len(calls) == 1
    assert calls[0].context.user_id == refresh_token.user.id


async def test_api_set_state_context(
    menuai: menuai, mock_api_client: TestClient, menuai_access_token: str
) -> None:
    """Test if the API sets right context if we set state."""
    await mock_api_client.post(
        "/api/states/light.kitchen",
        json={"state": "on"},
        headers={"authorization": f"Bearer {menuai_access_token}"},
    )

    refresh_token = menuai.auth.async_validate_access_token(menuai_access_token)

    state = menuai.states.get("light.kitchen")
    assert state.context.user_id == refresh_token.user.id


async def test_event_stream_requires_admin(
    menuai: menuai, mock_api_client: TestClient, menuai_admin_user: MockUser
) -> None:
    """Test user needs to be admin to access event stream."""
    menuai_admin_user.groups = []
    resp = await mock_api_client.get("/api/stream")
    assert resp.status == HTTPStatus.UNAUTHORIZED


async def test_states(
    menuai: menuai, mock_api_client: TestClient, menuai_admin_user: MockUser
) -> None:
    """Test fetching all states as admin."""
    menuai.states.async_set("test.entity", "hello")
    menuai.states.async_set("test.entity2", "hello")
    resp = await mock_api_client.get(const.URL_API_STATES)
    assert resp.status == HTTPStatus.OK
    json = await resp.json()
    assert len(json) == 2
    assert json[0]["entity_id"] == "test.entity"
    assert json[1]["entity_id"] == "test.entity2"


async def test_states_view_filters(
    menuai: menuai,
    menuai_read_only_user: MockUser,
    menuai_client: ClientSessionGenerator,
) -> None:
    """Test filtering only visible states."""
    assert not menuai_read_only_user.is_admin
    menuai_read_only_user.mock_policy({"entities": {"entity_ids": {"test.entity": True}}})
    await async_setup_component(menuai, "api", {})
    read_only_user_credential = Credentials(
        id="mock-read-only-credential-id",
        auth_provider_type="menuai",
        auth_provider_id=None,
        data={"username": "readonly"},
        is_new=False,
    )
    await menuai.auth.async_link_user(menuai_read_only_user, read_only_user_credential)

    refresh_token = await menuai.auth.async_create_refresh_token(
        menuai_read_only_user, CLIENT_ID, credential=read_only_user_credential
    )
    token = menuai.auth.async_create_access_token(refresh_token)
    mock_api_client = await menuai_client(token)
    menuai.states.async_set("test.entity", "hello")
    menuai.states.async_set("test.not_visible_entity", "invisible")
    resp = await mock_api_client.get(const.URL_API_STATES)
    assert resp.status == HTTPStatus.OK
    json = await resp.json()
    assert len(json) == 1
    assert json[0]["entity_id"] == "test.entity"


async def test_get_entity_state_read_perm(
    menuai: menuai, mock_api_client: TestClient, menuai_admin_user: MockUser
) -> None:
    """Test getting a state requires read permission."""
    menuai_admin_user.mock_policy({})
    menuai_admin_user.groups = []
    assert menuai_admin_user.is_admin is False
    resp = await mock_api_client.get("/api/states/light.test")
    assert resp.status == HTTPStatus.UNAUTHORIZED


async def test_post_entity_state_admin(
    menuai: menuai, mock_api_client: TestClient, menuai_admin_user: MockUser
) -> None:
    """Test updating state requires admin."""
    menuai_admin_user.groups = []
    resp = await mock_api_client.post("/api/states/light.test")
    assert resp.status == HTTPStatus.UNAUTHORIZED


async def test_delete_entity_state_admin(
    menuai: menuai, mock_api_client: TestClient, menuai_admin_user: MockUser
) -> None:
    """Test deleting entity requires admin."""
    menuai_admin_user.groups = []
    resp = await mock_api_client.delete("/api/states/light.test")
    assert resp.status == HTTPStatus.UNAUTHORIZED


async def test_post_event_admin(
    menuai: menuai, mock_api_client: TestClient, menuai_admin_user: MockUser
) -> None:
    """Test sending event requires admin."""
    menuai_admin_user.groups = []
    resp = await mock_api_client.post("/api/events/state_changed")
    assert resp.status == HTTPStatus.UNAUTHORIZED


async def test_rendering_template_admin(
    menuai: menuai, mock_api_client: TestClient, menuai_admin_user: MockUser
) -> None:
    """Test rendering a template requires admin."""
    menuai_admin_user.groups = []
    resp = await mock_api_client.post(const.URL_API_TEMPLATE)
    assert resp.status == HTTPStatus.UNAUTHORIZED


async def test_api_call_service_not_found(
    menuai: menuai, mock_api_client: TestClient
) -> None:
    """Test if the API fails 400 if unknown service."""
    resp = await mock_api_client.post("/api/services/test_domain/test_service")
    assert resp.status == HTTPStatus.BAD_REQUEST


async def test_api_call_service_bad_data(
    menuai: menuai, mock_api_client: TestClient
) -> None:
    """Test if the API fails 400 if unknown service."""
    test_value = []

    @ha.callback
    def listener(service_call):
        """Record that our service got called."""
        test_value.append(1)

    menuai.services.async_register(
        "test_domain", "test_service", listener, schema=vol.Schema({"hello": str})
    )

    resp = await mock_api_client.post(
        "/api/services/test_domain/test_service", json={"hello": 5}
    )
    assert resp.status == HTTPStatus.BAD_REQUEST


async def test_api_status(menuai: menuai, mock_api_client: TestClient) -> None:
    """Test getting the api status."""
    resp = await mock_api_client.get("/api/")
    assert resp.status == HTTPStatus.OK
    json = await resp.json()
    assert json["message"] == "API running."


async def test_api_core_state(menuai: menuai, mock_api_client: TestClient) -> None:
    """Test getting core status."""
    resp = await mock_api_client.get("/api/core/state")
    assert resp.status == HTTPStatus.OK
    json = await resp.json()
    assert json == {
        "state": "RUNNING",
        "recorder_state": {"migration_in_progress": False, "migration_is_live": False},
    }


@pytest.mark.parametrize(
    ("migration_in_progress", "migration_is_live"),
    [
        (False, False),
        (False, True),
        (True, False),
        (True, True),
    ],
)
async def test_api_core_state_recorder_migrating(
    menuai: menuai,
    mock_api_client: TestClient,
    migration_in_progress: bool,
    migration_is_live: bool,
) -> None:
    """Test getting core status."""
    with (
        patch(
            "menuai.helpers.recorder.async_migration_in_progress",
            return_value=migration_in_progress,
        ),
        patch(
            "menuai.helpers.recorder.async_migration_is_live",
            return_value=migration_is_live,
        ),
    ):
        resp = await mock_api_client.get("/api/core/state")
    assert resp.status == HTTPStatus.OK
    json = await resp.json()
    expected_recorder_state = {
        "migration_in_progress": migration_in_progress,
        "migration_is_live": migration_is_live,
    }
    assert json == {"state": "RUNNING", "recorder_state": expected_recorder_state}
