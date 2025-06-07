"""Test Airly system health."""

import asyncio

from aiohttp import ClientError

from menuai.components.airly.const import DOMAIN
from menuai.core import menuai
from menuai.setup import async_setup_component

from . import init_integration

from tests.common import get_system_health_info
from tests.test_util.aiohttp import AiohttpClientMocker


async def test_airly_system_health(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test Airly system health."""
    aioclient_mock.get("https://airapi.airly.eu/v2/", text="")

    await init_integration(menuai, aioclient_mock)
    assert await async_setup_component(menuai, "system_health", {})
    await menuai.async_block_till_done()

    info = await get_system_health_info(menuai, DOMAIN)

    for key, val in info.items():
        if asyncio.iscoroutine(val):
            info[key] = await val

    assert info["can_reach_server"] == "ok"
    assert info["requests_remaining"] == 42
    assert info["requests_per_day"] == 100


async def test_airly_system_health_fail(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test Airly system health."""
    aioclient_mock.get("https://airapi.airly.eu/v2/", exc=ClientError)

    await init_integration(menuai, aioclient_mock)
    assert await async_setup_component(menuai, "system_health", {})
    await menuai.async_block_till_done()

    info = await get_system_health_info(menuai, DOMAIN)

    for key, val in info.items():
        if asyncio.iscoroutine(val):
            info[key] = await val

    assert info["can_reach_server"] == {"type": "failed", "error": "unreachable"}
    assert info["requests_remaining"] == 42
    assert info["requests_per_day"] == 100
