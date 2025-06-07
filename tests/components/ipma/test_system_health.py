"""Test ipma system health."""

import asyncio

from menuai.components.ipma.system_health import IPMA_API_URL
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import get_system_health_info
from tests.test_util.aiohttp import AiohttpClientMocker


async def test_ipma_system_health(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test ipma system health."""
    aioclient_mock.get(IPMA_API_URL, json={"result": "ok", "data": {}})

    menuai.config.components.add("ipma")
    assert await async_setup_component(menuai, "system_health", {})
    await menuai.async_block_till_done()

    info = await get_system_health_info(menuai, "ipma")

    for key, val in info.items():
        if asyncio.iscoroutine(val):
            info[key] = await val

    assert info == {"api_endpoint_reachable": "ok"}
