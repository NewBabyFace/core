"""Test Discovergy system health."""

import asyncio

from aiohttp import ClientError
from pydiscovergy.const import API_BASE

from menuai.components.discovergy.const import DOMAIN
from menuai.core import menuai
from menuai.loader import async_get_integration
from menuai.setup import async_setup_component

from tests.common import get_system_health_info
from tests.test_util.aiohttp import AiohttpClientMocker


async def test_discovergy_system_health(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test Discovergy system health."""
    aioclient_mock.get(API_BASE, text="")
    integration = await async_get_integration(menuai, DOMAIN)
    await integration.async_get_component()
    menuai.config.components.add(DOMAIN)
    assert await async_setup_component(menuai, "system_health", {})
    await menuai.async_block_till_done()

    info = await get_system_health_info(menuai, DOMAIN)

    for key, val in info.items():
        if asyncio.iscoroutine(val):
            info[key] = await val

    assert info == {"api_endpoint_reachable": "ok"}


async def test_discovergy_system_health_fail(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test Discovergy system health."""
    aioclient_mock.get(API_BASE, exc=ClientError)
    integration = await async_get_integration(menuai, DOMAIN)
    await integration.async_get_component()
    menuai.config.components.add(DOMAIN)
    assert await async_setup_component(menuai, "system_health", {})
    await menuai.async_block_till_done()

    info = await get_system_health_info(menuai, DOMAIN)

    for key, val in info.items():
        if asyncio.iscoroutine(val):
            info[key] = await val

    assert info == {
        "api_endpoint_reachable": {"type": "failed", "error": "unreachable"}
    }
