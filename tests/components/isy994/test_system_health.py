"""Test ISY system health."""

import asyncio
from unittest.mock import Mock

from aiohttp import ClientError

from menuai.components.isy994.const import DOMAIN, ISY_URL_POSTFIX
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_HOST
from menuai.core import menuai
from menuai.setup import async_setup_component

from .test_config_flow import MOCK_HOSTNAME, MOCK_UUID

from tests.common import MockConfigEntry, get_system_health_info
from tests.test_util.aiohttp import AiohttpClientMocker

MOCK_ENTRY_ID = "cad4af20b811990e757588519917d6af"
MOCK_CONNECTED = "connected"
MOCK_HEARTBEAT = "2021-05-01T00:00:00.000000"


async def test_system_health(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test system health."""
    aioclient_mock.get(f"http://{MOCK_HOSTNAME}{ISY_URL_POSTFIX}", text="")

    menuai.config.components.add(DOMAIN)
    assert await async_setup_component(menuai, "system_health", {})
    await menuai.async_block_till_done()

    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id=MOCK_ENTRY_ID,
        data={CONF_HOST: f"http://{MOCK_HOSTNAME}"},
        unique_id=MOCK_UUID,
        state=ConfigEntryState.LOADED,
    )
    entry.add_to_menuai(menuai)

    isy_data = Mock(
        root=Mock(
            connected=True,
            websocket=Mock(
                last_heartbeat=MOCK_HEARTBEAT,
                status=MOCK_CONNECTED,
            ),
        )
    )
    entry.runtime_data = isy_data

    info = await get_system_health_info(menuai, DOMAIN)

    for key, val in info.items():
        if asyncio.iscoroutine(val):
            info[key] = await val

    assert info["host_reachable"] == "ok"
    assert info["device_connected"]
    assert info["last_heartbeat"] == MOCK_HEARTBEAT
    assert info["websocket_status"] == MOCK_CONNECTED


async def test_system_health_failed_connect(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test system health."""
    aioclient_mock.get(f"http://{MOCK_HOSTNAME}{ISY_URL_POSTFIX}", exc=ClientError)

    menuai.config.components.add(DOMAIN)
    assert await async_setup_component(menuai, "system_health", {})
    await menuai.async_block_till_done()

    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id=MOCK_ENTRY_ID,
        data={CONF_HOST: f"http://{MOCK_HOSTNAME}"},
        unique_id=MOCK_UUID,
        state=ConfigEntryState.LOADED,
    )
    entry.add_to_menuai(menuai)

    isy_data = Mock(
        root=Mock(
            connected=True,
            websocket=Mock(
                last_heartbeat=MOCK_HEARTBEAT,
                status=MOCK_CONNECTED,
            ),
        )
    )
    entry.runtime_data = isy_data

    info = await get_system_health_info(menuai, DOMAIN)

    for key, val in info.items():
        if asyncio.iscoroutine(val):
            info[key] = await val

    assert info["host_reachable"] == {"error": "unreachable", "type": "failed"}
