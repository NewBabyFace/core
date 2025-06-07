"""Test cases for the API stream sensor."""

from menuai.auth.providers.menuai import menuaiAuthProvider
from menuai.components.websocket_api.auth import TYPE_AUTH_REQUIRED
from menuai.components.websocket_api.http import URL
from menuai.core import menuai
from menuai.setup import async_setup_component

from .test_auth import test_auth_active_with_token

from tests.typing import ClientSessionGenerator


async def test_websocket_api(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    menuai_access_token: str,
    local_auth: menuaiAuthProvider,
) -> None:
    """Test API streams."""
    await async_setup_component(
        menuai, "sensor", {"sensor": {"platform": "websocket_api"}}
    )
    await menuai.async_block_till_done()

    client = await menuai_client_no_auth()
    ws = await client.ws_connect(URL)

    auth_ok = await ws.receive_json()

    assert auth_ok["type"] == TYPE_AUTH_REQUIRED

    ws.client = client

    state = menuai.states.get("sensor.connected_clients")
    assert state.state == "0"

    await test_auth_active_with_token(menuai, ws, menuai_access_token)

    state = menuai.states.get("sensor.connected_clients")
    assert state.state == "1"

    await ws.close()
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.connected_clients")
    assert state.state == "0"
