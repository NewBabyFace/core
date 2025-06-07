"""The tests for the analytics ."""

from unittest.mock import patch

import pytest

from menuai.components.analytics.const import ANALYTICS_ENDPOINT_URL, DOMAIN
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.test_util.aiohttp import AiohttpClientMocker
from tests.typing import WebSocketGenerator

MOCK_VERSION = "1970.1.0"


async def test_setup(menuai: menuai) -> None:
    """Test setup of the integration."""
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
    await menuai.async_block_till_done()

    assert DOMAIN in menuai.data


@pytest.mark.usefixtures("supervisor_client")
async def test_websocket(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test WebSocket commands."""
    aioclient_mock.post(ANALYTICS_ENDPOINT_URL, status=200)
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
    await menuai.async_block_till_done()

    ws_client = await menuai_ws_client(menuai)
    await ws_client.send_json_auto_id({"type": "analytics"})

    response = await ws_client.receive_json()

    assert response["success"]

    with patch("menuai.components.analytics.analytics.HA_VERSION", MOCK_VERSION):
        await ws_client.send_json_auto_id(
            {"type": "analytics/preferences", "preferences": {"base": True}}
        )
        response = await ws_client.receive_json()
    assert len(aioclient_mock.mock_calls) == 1
    assert response["result"]["preferences"]["base"]

    await ws_client.send_json_auto_id({"type": "analytics"})
    response = await ws_client.receive_json()
    assert response["result"]["preferences"]["base"]
