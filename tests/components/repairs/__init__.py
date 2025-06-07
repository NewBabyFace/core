"""Tests for the repairs integration."""

from http import HTTPStatus
from typing import Any

from aiohttp.test_utils import TestClient

from menuai.components.repairs.issue_handler import (  # noqa: F401
    async_process_repairs_platforms,
)
from menuai.components.repairs.websocket_api import (
    RepairsFlowIndexView,
    RepairsFlowResourceView,
)
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.typing import WebSocketGenerator


async def get_repairs(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
):
    """Return the repairs list of issues."""
    assert await async_setup_component(menuai, "repairs", {})

    client = await menuai_ws_client(menuai)
    await menuai.async_block_till_done()

    await client.send_json({"id": 1, "type": "repairs/list_issues"})
    msg = await client.receive_json()

    client = await menuai_ws_client(menuai)
    await menuai.async_block_till_done()

    assert msg["id"] == 1
    assert msg["success"]
    assert msg["result"]

    return msg["result"]["issues"]


async def start_repair_fix_flow(
    client: TestClient, handler: str, issue_id: str
) -> dict[str, Any]:
    """Start a flow from an issue."""
    url = RepairsFlowIndexView.url
    resp = await client.post(url, json={"handler": handler, "issue_id": issue_id})
    assert resp.status == HTTPStatus.OK, f"Error: {resp.status}, {await resp.text()}"
    return await resp.json()


async def process_repair_fix_flow(
    client: TestClient, flow_id: str, json: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Return the repairs list of issues."""
    url = RepairsFlowResourceView.url.format(flow_id=flow_id)
    resp = await client.post(url, json=json)
    assert resp.status == HTTPStatus.OK, f"Error: {resp.status}, {await resp.text()}"
    return await resp.json()
