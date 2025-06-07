"""Fixtures for websocket tests."""

from aiohttp.test_utils import TestClient
import pytest

from menuai.components.websocket_api.auth import TYPE_AUTH_REQUIRED
from menuai.components.websocket_api.http import URL
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.typing import (
    ClientSessionGenerator,
    MockHAClientWebSocket,
    WebSocketGenerator,
)


@pytest.fixture
async def websocket_client(
    menuai: menuai, menuai_ws_client: WebSocketGenerator
) -> MockHAClientWebSocket:
    """Create a websocket client."""
    return await menuai_ws_client(menuai)


@pytest.fixture
async def no_auth_websocket_client(
    menuai: menuai, menuai_client_no_auth: ClientSessionGenerator
) -> TestClient:
    """Websocket connection that requires authentication."""
    assert await async_setup_component(menuai, "websocket_api", {})
    await menuai.async_block_till_done()

    client = await menuai_client_no_auth()
    ws = await client.ws_connect(URL)

    auth_ok = await ws.receive_json()
    assert auth_ok["type"] == TYPE_AUTH_REQUIRED

    ws.client = client
    yield ws

    if not ws.closed:
        await ws.close()
