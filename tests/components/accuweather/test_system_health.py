"""Test AccuWeather system health."""

import asyncio
from unittest.mock import AsyncMock

from aiohttp import ClientError

from menuai.components.accuweather.const import DOMAIN
from menuai.core import menuai
from menuai.setup import async_setup_component

from . import init_integration

from tests.common import get_system_health_info
from tests.test_util.aiohttp import AiohttpClientMocker


async def test_accuweather_system_health(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    mock_accuweather_client: AsyncMock,
) -> None:
    """Test AccuWeather system health."""
    aioclient_mock.get("https://dataservice.accuweather.com/", text="")

    await init_integration(menuai)
    assert await async_setup_component(menuai, "system_health", {})
    await menuai.async_block_till_done()

    info = await get_system_health_info(menuai, DOMAIN)

    for key, val in info.items():
        if asyncio.iscoroutine(val):
            info[key] = await val

    assert info == {
        "can_reach_server": "ok",
        "remaining_requests": 10,
    }


async def test_accuweather_system_health_fail(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    mock_accuweather_client: AsyncMock,
) -> None:
    """Test AccuWeather system health."""
    aioclient_mock.get("https://dataservice.accuweather.com/", exc=ClientError)

    await init_integration(menuai)
    assert await async_setup_component(menuai, "system_health", {})
    await menuai.async_block_till_done()

    info = await get_system_health_info(menuai, DOMAIN)

    for key, val in info.items():
        if asyncio.iscoroutine(val):
            info[key] = await val

    assert info == {
        "can_reach_server": {"type": "failed", "error": "unreachable"},
        "remaining_requests": 10,
    }
