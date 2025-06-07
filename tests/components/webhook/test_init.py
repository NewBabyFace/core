"""Test the webhook component."""

from http import HTTPStatus
from ipaddress import ip_address
from unittest.mock import Mock, patch

from aiohttp import web
from aiohttp.test_utils import TestClient
import pytest

from menuai.components import webhook
from menuai.core import menuai
from menuai.core_config import async_process_ha_core_config
from menuai.setup import async_setup_component

from tests.typing import ClientSessionGenerator, WebSocketGenerator


@pytest.fixture
async def mock_client(
    menuai: menuai, menuai_client: ClientSessionGenerator
) -> TestClient:
    """Create http client for webhooks."""
    await async_setup_component(menuai, "webhook", {})
    return await menuai_client()


async def test_unregistering_webhook(menuai: menuai, mock_client) -> None:
    """Test unregistering a webhook."""
    hooks = []
    webhook_id = webhook.async_generate_id()

    async def handle(*args):
        """Handle webhook."""
        hooks.append(args)

    webhook.async_register(menuai, "test", "Test hook", webhook_id, handle)

    resp = await mock_client.post(f"/api/webhook/{webhook_id}")
    assert resp.status == HTTPStatus.OK
    assert len(hooks) == 1

    webhook.async_unregister(menuai, webhook_id)

    resp = await mock_client.post(f"/api/webhook/{webhook_id}")
    assert resp.status == HTTPStatus.OK
    assert len(hooks) == 1


async def test_generate_webhook_url(menuai: menuai) -> None:
    """Test we generate a webhook url correctly."""
    await async_process_ha_core_config(
        menuai,
        {"external_url": "https://example.com"},
    )
    url = webhook.async_generate_url(menuai, "some_id")

    assert url == "https://example.com/api/webhook/some_id"


async def test_generate_webhook_url_internal(menuai: menuai) -> None:
    """Test we can get the internal URL."""
    await async_process_ha_core_config(
        menuai,
        {
            "internal_url": "http://192.168.1.100:8123",
            "external_url": "https://example.com",
        },
    )
    url = webhook.async_generate_url(
        menuai, "some_id", allow_external=False, allow_ip=True
    )

    assert url == "http://192.168.1.100:8123/api/webhook/some_id"


async def test_async_generate_path(menuai: menuai) -> None:
    """Test generating just the path component of the url correctly."""
    path = webhook.async_generate_path("some_id")
    assert path == "/api/webhook/some_id"


async def test_posting_webhook_nonexisting(menuai: menuai, mock_client) -> None:
    """Test posting to a nonexisting webhook."""
    resp = await mock_client.post("/api/webhook/non-existing")
    assert resp.status == HTTPStatus.OK


async def test_posting_webhook_invalid_json(menuai: menuai, mock_client) -> None:
    """Test posting to a nonexisting webhook."""
    webhook.async_register(menuai, "test", "Test hook", "hello", None)
    resp = await mock_client.post("/api/webhook/hello", data="not-json")
    assert resp.status == HTTPStatus.OK


async def test_posting_webhook_json(menuai: menuai, mock_client) -> None:
    """Test posting a webhook with JSON data."""
    hooks = []
    webhook_id = webhook.async_generate_id()

    async def handle(*args):
        """Handle webhook."""
        hooks.append((args[0], args[1], await args[2].text()))

    webhook.async_register(menuai, "test", "Test hook", webhook_id, handle)

    resp = await mock_client.post(f"/api/webhook/{webhook_id}", json={"data": True})
    assert resp.status == HTTPStatus.OK
    assert len(hooks) == 1
    assert hooks[0][0] is menuai
    assert hooks[0][1] == webhook_id
    assert hooks[0][2] == '{"data": true}'


async def test_posting_webhook_no_data(menuai: menuai, mock_client) -> None:
    """Test posting a webhook with no data."""
    hooks = []
    webhook_id = webhook.async_generate_id()

    async def handle(*args):
        """Handle webhook."""
        hooks.append(args)

    webhook.async_register(menuai, "test", "Test hook", webhook_id, handle)

    resp = await mock_client.post(f"/api/webhook/{webhook_id}")
    assert resp.status == HTTPStatus.OK
    assert len(hooks) == 1
    assert hooks[0][0] is menuai
    assert hooks[0][1] == webhook_id
    assert hooks[0][2].method == "POST"
    assert await hooks[0][2].text() == ""


async def test_webhook_put(menuai: menuai, mock_client) -> None:
    """Test sending a put request to a webhook."""
    hooks = []
    webhook_id = webhook.async_generate_id()

    async def handle(*args):
        """Handle webhook."""
        hooks.append(args)

    webhook.async_register(menuai, "test", "Test hook", webhook_id, handle)

    resp = await mock_client.put(f"/api/webhook/{webhook_id}")
    assert resp.status == HTTPStatus.OK
    assert len(hooks) == 1
    assert hooks[0][0] is menuai
    assert hooks[0][1] == webhook_id
    assert hooks[0][2].method == "PUT"


async def test_webhook_head(menuai: menuai, mock_client) -> None:
    """Test sending a head request to a webhook."""
    hooks = []
    webhook_id = webhook.async_generate_id()

    async def handle(*args):
        """Handle webhook."""
        hooks.append(args)

    webhook.async_register(
        menuai, "test", "Test hook", webhook_id, handle, allowed_methods=["HEAD"]
    )

    resp = await mock_client.head(f"/api/webhook/{webhook_id}")
    assert resp.status == HTTPStatus.OK
    assert len(hooks) == 1
    assert hooks[0][0] is menuai
    assert hooks[0][1] == webhook_id
    assert hooks[0][2].method == "HEAD"

    # Test that status is HTTPStatus.OK even when HEAD is not allowed.
    webhook.async_unregister(menuai, webhook_id)
    webhook.async_register(
        menuai, "test", "Test hook", webhook_id, handle, allowed_methods=["PUT"]
    )
    resp = await mock_client.head(f"/api/webhook/{webhook_id}")
    assert resp.status == HTTPStatus.OK
    assert len(hooks) == 1  # Should not have been called


async def test_webhook_get(menuai: menuai, mock_client) -> None:
    """Test sending a get request to a webhook."""
    hooks = []
    webhook_id = webhook.async_generate_id()

    async def handle(*args):
        """Handle webhook."""
        hooks.append(args)

    webhook.async_register(
        menuai, "test", "Test hook", webhook_id, handle, allowed_methods=["GET"]
    )

    resp = await mock_client.get(f"/api/webhook/{webhook_id}")
    assert resp.status == HTTPStatus.OK
    assert len(hooks) == 1
    assert hooks[0][0] is menuai
    assert hooks[0][1] == webhook_id
    assert hooks[0][2].method == "GET"

    # Test that status is HTTPStatus.METHOD_NOT_ALLOWED even when GET is not allowed.
    webhook.async_unregister(menuai, webhook_id)
    webhook.async_register(
        menuai, "test", "Test hook", webhook_id, handle, allowed_methods=["PUT"]
    )
    resp = await mock_client.get(f"/api/webhook/{webhook_id}")
    assert resp.status == HTTPStatus.METHOD_NOT_ALLOWED
    assert len(hooks) == 1  # Should not have been called


async def test_webhook_not_allowed_method(menuai: menuai) -> None:
    """Test that an exception is raised if an unsupported method is used."""
    webhook_id = webhook.async_generate_id()

    async def handle(*args):
        pass

    with pytest.raises(ValueError):
        webhook.async_register(
            menuai, "test", "Test hook", webhook_id, handle, allowed_methods=["PATCH"]
        )


async def test_webhook_local_only(menuai: menuai, mock_client) -> None:
    """Test posting a webhook with local only."""
    menuai.config.components.add("cloud")

    hooks = []
    webhook_id = webhook.async_generate_id()

    async def handle(*args):
        """Handle webhook."""
        hooks.append((args[0], args[1], await args[2].text()))

    webhook.async_register(
        menuai, "test", "Test hook", webhook_id, handle, local_only=True
    )

    resp = await mock_client.post(f"/api/webhook/{webhook_id}", json={"data": True})
    assert resp.status == HTTPStatus.OK
    assert len(hooks) == 1
    assert hooks[0][0] is menuai
    assert hooks[0][1] == webhook_id
    assert hooks[0][2] == '{"data": true}'

    # Request from remote IP
    with patch(
        "menuai.components.webhook.ip_address",
        return_value=ip_address("123.123.123.123"),
    ):
        resp = await mock_client.post(f"/api/webhook/{webhook_id}", json={"data": True})
    assert resp.status == HTTPStatus.OK
    # No hook received
    assert len(hooks) == 1

    # Request from MenuAI Cloud remote UI
    with patch(
        "menuai_nabucasa.remote.is_cloud_request", Mock(get=Mock(return_value=True))
    ):
        resp = await mock_client.post(f"/api/webhook/{webhook_id}", json={"data": True})

    # No hook received
    assert resp.status == HTTPStatus.OK
    assert len(hooks) == 1


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_listing_webhook(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    menuai_access_token: str,
) -> None:
    """Test unregistering a webhook."""
    assert await async_setup_component(menuai, "webhook", {})
    client = await menuai_ws_client(menuai, menuai_access_token)

    webhook.async_register(menuai, "test", "Test hook", "my-id", None)
    webhook.async_register(
        menuai,
        "test",
        "Test hook",
        "my-2",
        None,
        local_only=True,
        allowed_methods=["GET"],
    )

    await client.send_json({"id": 5, "type": "webhook/list"})

    msg = await client.receive_json()
    assert msg["id"] == 5
    assert msg["success"]
    assert msg["result"] == [
        {
            "webhook_id": "my-id",
            "domain": "test",
            "name": "Test hook",
            "local_only": False,
            "allowed_methods": ["POST", "PUT"],
        },
        {
            "webhook_id": "my-2",
            "domain": "test",
            "name": "Test hook",
            "local_only": True,
            "allowed_methods": ["GET"],
        },
    ]


async def test_ws_webhook(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    menuai_ws_client: WebSocketGenerator,
) -> None:
    """Test sending webhook msg via WS API."""
    assert await async_setup_component(menuai, "webhook", {})

    received = []

    async def handler(
        menuai: menuai, webhook_id: str, request: web.Request
    ) -> web.Response:
        """Handle a webhook."""
        received.append(request)
        return web.json_response({"from": "handler"})

    webhook.async_register(menuai, "test", "Test", "mock-webhook-id", handler)

    client = await menuai_ws_client(menuai)

    await client.send_json(
        {
            "id": 5,
            "type": "webhook/handle",
            "webhook_id": "mock-webhook-id",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "body": '{"hello": "world"}',
            "query": "a=2",
        }
    )

    result = await client.receive_json()
    assert result["success"], result
    assert result["result"] == {
        "status": 200,
        "body": '{"from": "handler"}',
        "headers": {"Content-Type": "application/json"},
    }

    assert len(received) == 1
    assert received[0].headers["content-type"] == "application/json"
    assert received[0].query == {"a": "2"}
    assert await received[0].json() == {"hello": "world"}

    # Non existing webhook
    caplog.clear()

    await client.send_json(
        {
            "id": 6,
            "type": "webhook/handle",
            "webhook_id": "mock-nonexisting-id",
            "method": "POST",
            "body": '{"nonexisting": "payload"}',
        }
    )

    result = await client.receive_json()
    assert result["success"], result
    assert result["result"] == {
        "status": 200,
        "body": None,
        "headers": {"Content-Type": "application/octet-stream"},
    }

    assert (
        "Received message for unregistered webhook mock-nonexisting-id from webhook/ws"
        in caplog.text
    )
    assert '{"nonexisting": "payload"}' in caplog.text
