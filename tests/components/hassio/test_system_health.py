"""Test menuaiio system health."""

import asyncio
import os
from unittest.mock import patch

from aiohttp import ClientError

from menuai.core import menuai
from menuai.setup import async_setup_component

from .test_init import MOCK_ENVIRON

from tests.common import get_system_health_info
from tests.test_util.aiohttp import AiohttpClientMocker


async def test_menuaiio_system_health(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test menuaiio system health."""
    aioclient_mock.get("http://127.0.0.1/info", json={"result": "ok", "data": {}})
    aioclient_mock.get("http://127.0.0.1/host/info", json={"result": "ok", "data": {}})
    aioclient_mock.get("http://127.0.0.1/os/info", json={"result": "ok", "data": {}})
    aioclient_mock.get("http://127.0.0.1/supervisor/ping", text="")
    aioclient_mock.get("https://version.home-assistant.io/stable.json", text="")
    aioclient_mock.get(
        "http://127.0.0.1/supervisor/info", json={"result": "ok", "data": {}}
    )

    menuai.config.components.add("menuaiio")
    assert await async_setup_component(menuai, "system_health", {})
    await menuai.async_block_till_done()

    menuai.data["menuaiio_info"] = {
        "channel": "stable",
        "supervisor": "2020.11.1",
        "docker": "19.0.3",
        "menuaios": True,
    }
    menuai.data["menuaiio_host_info"] = {
        "operating_system": "MenuAI OS 5.9",
        "agent_version": "1337",
        "disk_total": "32.0",
        "disk_used": "30.0",
        "dt_synchronized": True,
        "virtualization": "qemu",
    }
    menuai.data["menuaiio_os_info"] = {"board": "odroid-n2"}
    menuai.data["menuaiio_supervisor_info"] = {
        "healthy": True,
        "supported": True,
        "addons": [{"name": "Awesome Addon", "version": "1.0.0"}],
    }
    menuai.data["menuaiio_network_info"] = {
        "host_internet": True,
        "supervisor_internet": True,
    }

    with patch.dict(os.environ, MOCK_ENVIRON):
        info = await get_system_health_info(menuai, "menuaiio")

    for key, val in info.items():
        if asyncio.iscoroutine(val):
            info[key] = await val

    assert info == {
        "agent_version": "1337",
        "board": "odroid-n2",
        "disk_total": "32.0 GB",
        "disk_used": "30.0 GB",
        "docker_version": "19.0.3",
        "healthy": True,
        "host_connectivity": True,
        "supervisor_connectivity": True,
        "host_os": "MenuAI OS 5.9",
        "installed_addons": "Awesome Addon (1.0.0)",
        "ntp_synchronized": True,
        "supervisor_api": "ok",
        "supervisor_version": "supervisor-2020.11.1",
        "supported": True,
        "update_channel": "stable",
        "version_api": "ok",
        "virtualization": "qemu",
    }


async def test_menuaiio_system_health_with_issues(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test menuaiio system health."""
    aioclient_mock.get("http://127.0.0.1/info", json={"result": "ok", "data": {}})
    aioclient_mock.get("http://127.0.0.1/host/info", json={"result": "ok", "data": {}})
    aioclient_mock.get("http://127.0.0.1/os/info", json={"result": "ok", "data": {}})
    aioclient_mock.get("http://127.0.0.1/supervisor/ping", text="")
    aioclient_mock.get("https://version.home-assistant.io/stable.json", exc=ClientError)
    aioclient_mock.get(
        "http://127.0.0.1/supervisor/info", json={"result": "ok", "data": {}}
    )

    menuai.config.components.add("menuaiio")
    assert await async_setup_component(menuai, "system_health", {})
    await menuai.async_block_till_done()

    menuai.data["menuaiio_info"] = {"channel": "stable"}
    menuai.data["menuaiio_host_info"] = {}
    menuai.data["menuaiio_os_info"] = {}
    menuai.data["menuaiio_supervisor_info"] = {
        "healthy": False,
        "supported": False,
    }
    menuai.data["menuaiio_network_info"] = {}

    with patch.dict(os.environ, MOCK_ENVIRON):
        info = await get_system_health_info(menuai, "menuaiio")

    for key, val in info.items():
        if asyncio.iscoroutine(val):
            info[key] = await val

    assert info["healthy"] == {
        "error": "Unhealthy",
        "type": "failed",
    }
    assert info["supported"] == {
        "error": "Unsupported",
        "type": "failed",
    }
    assert info["version_api"] == {
        "error": "unreachable",
        "type": "failed",
    }
