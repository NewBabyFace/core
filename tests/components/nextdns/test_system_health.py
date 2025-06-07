"""Test NextDNS system health."""

import asyncio

from aiohttp import ClientError
from nextdns.const import API_ENDPOINT

from menuai.components.nextdns.const import DOMAIN
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import get_system_health_info
from tests.test_util.aiohttp import AiohttpClientMocker


async def test_nextdns_system_health(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test NextDNS system health."""
    aioclient_mock.get(API_ENDPOINT, text="")
    menuai.config.components.add(DOMAIN)
    assert await async_setup_component(menuai, "system_health", {})
    await menuai.async_block_till_done()

    info = await get_system_health_info(menuai, DOMAIN)

    for key, val in info.items():
        if asyncio.iscoroutine(val):
            info[key] = await val

    assert info == {"can_reach_server": "ok"}


async def test_nextdns_system_health_fail(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test NextDNS system health."""
    aioclient_mock.get(API_ENDPOINT, exc=ClientError)
    menuai.config.components.add(DOMAIN)
    assert await async_setup_component(menuai, "system_health", {})
    await menuai.async_block_till_done()

    info = await get_system_health_info(menuai, DOMAIN)

    for key, val in info.items():
        if asyncio.iscoroutine(val):
            info[key] = await val

    assert info == {"can_reach_server": {"type": "failed", "error": "unreachable"}}
