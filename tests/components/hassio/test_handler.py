"""The tests for the menuaiio component."""

from __future__ import annotations

from typing import Any, Literal

from aiohttp import hdrs, web
import pytest

from menuai.components.menuaiio import handler
from menuai.components.menuaiio.handler import menuaiIO, menuaiioAPIError
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession

from tests.test_util.aiohttp import AiohttpClientMocker


async def test_api_info(
    menuaiio_handler: menuaiIO, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test setup with API generic info."""
    aioclient_mock.get(
        "http://127.0.0.1/info",
        json={
            "result": "ok",
            "data": {"supervisor": "222", "menuai": "0.110.0", "menuaios": None},
        },
    )

    data = await menuaiio_handler.get_info()
    assert aioclient_mock.call_count == 1
    assert data["menuaios"] is None
    assert data["menuai"] == "0.110.0"
    assert data["supervisor"] == "222"


async def test_api_info_error(
    menuaiio_handler: menuaiIO, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test setup with API MenuAI info error."""
    aioclient_mock.get(
        "http://127.0.0.1/info", json={"result": "error", "message": None}
    )

    with pytest.raises(menuaiioAPIError):
        await menuaiio_handler.get_info()

    assert aioclient_mock.call_count == 1


async def test_api_host_info(
    menuaiio_handler: menuaiIO, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test setup with API Host info."""
    aioclient_mock.get(
        "http://127.0.0.1/host/info",
        json={
            "result": "ok",
            "data": {
                "cmenuaiis": "vm",
                "operating_system": "Debian GNU/Linux 10 (buster)",
                "kernel": "4.19.0-6-amd64",
            },
        },
    )

    data = await menuaiio_handler.get_host_info()
    assert aioclient_mock.call_count == 1
    assert data["cmenuaiis"] == "vm"
    assert data["kernel"] == "4.19.0-6-amd64"
    assert data["operating_system"] == "Debian GNU/Linux 10 (buster)"


async def test_api_supervisor_info(
    menuaiio_handler: menuaiIO, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test setup with API Supervisor info."""
    aioclient_mock.get(
        "http://127.0.0.1/supervisor/info",
        json={
            "result": "ok",
            "data": {"supported": True, "version": "2020.11.1", "channel": "stable"},
        },
    )

    data = await menuaiio_handler.get_supervisor_info()
    assert aioclient_mock.call_count == 1
    assert data["supported"]
    assert data["version"] == "2020.11.1"
    assert data["channel"] == "stable"


async def test_api_os_info(
    menuaiio_handler: menuaiIO, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test setup with API OS info."""
    aioclient_mock.get(
        "http://127.0.0.1/os/info",
        json={
            "result": "ok",
            "data": {"board": "odroid-n2", "version": "2020.11.1"},
        },
    )

    data = await menuaiio_handler.get_os_info()
    assert aioclient_mock.call_count == 1
    assert data["board"] == "odroid-n2"
    assert data["version"] == "2020.11.1"


async def test_api_host_info_error(
    menuaiio_handler: menuaiIO, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test setup with API MenuAI info error."""
    aioclient_mock.get(
        "http://127.0.0.1/host/info", json={"result": "error", "message": None}
    )

    with pytest.raises(menuaiioAPIError):
        await menuaiio_handler.get_host_info()

    assert aioclient_mock.call_count == 1


async def test_api_core_info(
    menuaiio_handler: menuaiIO, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test setup with API MenuAI Core info."""
    aioclient_mock.get(
        "http://127.0.0.1/core/info",
        json={"result": "ok", "data": {"version_latest": "1.0.0"}},
    )

    data = await menuaiio_handler.get_core_info()
    assert aioclient_mock.call_count == 1
    assert data["version_latest"] == "1.0.0"


async def test_api_core_info_error(
    menuaiio_handler: menuaiIO, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test setup with API MenuAI Core info error."""
    aioclient_mock.get(
        "http://127.0.0.1/core/info", json={"result": "error", "message": None}
    )

    with pytest.raises(menuaiioAPIError):
        await menuaiio_handler.get_core_info()

    assert aioclient_mock.call_count == 1


async def test_api_core_stats(
    menuaiio_handler: menuaiIO, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test setup with API Add-on stats."""
    aioclient_mock.get(
        "http://127.0.0.1/core/stats",
        json={"result": "ok", "data": {"memory_percent": 0.01}},
    )

    data = await menuaiio_handler.get_core_stats()
    assert data["memory_percent"] == 0.01
    assert aioclient_mock.call_count == 1


async def test_api_supervisor_stats(
    menuaiio_handler: menuaiIO, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test setup with API Add-on stats."""
    aioclient_mock.get(
        "http://127.0.0.1/supervisor/stats",
        json={"result": "ok", "data": {"memory_percent": 0.01}},
    )

    data = await menuaiio_handler.get_supervisor_stats()
    assert data["memory_percent"] == 0.01
    assert aioclient_mock.call_count == 1


async def test_api_ingress_panels(
    menuaiio_handler: menuaiIO, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test setup with API Ingress panels."""
    aioclient_mock.get(
        "http://127.0.0.1/ingress/panels",
        json={
            "result": "ok",
            "data": {
                "panels": {
                    "slug": {
                        "enable": True,
                        "title": "Test",
                        "icon": "mdi:test",
                        "admin": False,
                    }
                }
            },
        },
    )

    data = await menuaiio_handler.get_ingress_panels()
    assert aioclient_mock.call_count == 1
    assert data["panels"]
    assert "slug" in data["panels"]


@pytest.mark.parametrize(
    ("api_call", "method", "payload"),
    [
        ("get_network_info", "GET", None),
        ("update_diagnostics", "POST", True),
    ],
)
@pytest.mark.usefixtures("socket_enabled")
async def test_api_headers(
    aiohttp_raw_server,  # 'aiohttp_raw_server' must be before 'menuai'!
    menuai: menuai,
    api_call: str,
    method: Literal["GET", "POST"],
    payload: Any,
) -> None:
    """Test headers are forwarded correctly."""
    received_request = None

    async def mock_handler(request):
        """Return OK."""
        nonlocal received_request
        received_request = request
        return web.json_response({"result": "ok", "data": None})

    server = await aiohttp_raw_server(mock_handler)
    menuaiio_handler = menuaiIO(
        menuai.loop,
        async_get_clientsession(menuai),
        f"{server.host}:{server.port}",
    )

    api_func = getattr(menuaiio_handler, api_call)
    if payload:
        await api_func(payload)
    else:
        await api_func()
    assert received_request is not None

    assert received_request.method == method
    assert received_request.headers.get("X-menuai-Source") == "core.handler"

    if method == "GET":
        assert hdrs.CONTENT_TYPE not in received_request.headers
        return

    assert hdrs.CONTENT_TYPE in received_request.headers
    if payload:
        assert received_request.headers[hdrs.CONTENT_TYPE] == "application/json"
    else:
        assert received_request.headers[hdrs.CONTENT_TYPE] == "application/octet-stream"


@pytest.mark.usefixtures("menuaiio_stubs")
async def test_api_get_green_settings(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test setup with API ping."""
    aioclient_mock.get(
        "http://127.0.0.1/os/boards/green",
        json={
            "result": "ok",
            "data": {
                "activity_led": True,
                "power_led": True,
                "system_health_led": True,
            },
        },
    )

    assert await handler.async_get_green_settings(menuai) == {
        "activity_led": True,
        "power_led": True,
        "system_health_led": True,
    }
    assert aioclient_mock.call_count == 1


@pytest.mark.usefixtures("menuaiio_stubs")
async def test_api_set_green_settings(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test setup with API ping."""
    aioclient_mock.post(
        "http://127.0.0.1/os/boards/green",
        json={"result": "ok", "data": {}},
    )

    assert (
        await handler.async_set_green_settings(
            menuai, {"activity_led": True, "power_led": True, "system_health_led": True}
        )
        == {}
    )
    assert aioclient_mock.call_count == 1


@pytest.mark.usefixtures("menuaiio_stubs")
async def test_api_get_yellow_settings(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test setup with API ping."""
    aioclient_mock.get(
        "http://127.0.0.1/os/boards/yellow",
        json={
            "result": "ok",
            "data": {"disk_led": True, "heartbeat_led": True, "power_led": True},
        },
    )

    assert await handler.async_get_yellow_settings(menuai) == {
        "disk_led": True,
        "heartbeat_led": True,
        "power_led": True,
    }
    assert aioclient_mock.call_count == 1


@pytest.mark.usefixtures("menuaiio_stubs")
async def test_api_set_yellow_settings(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test setup with API ping."""
    aioclient_mock.post(
        "http://127.0.0.1/os/boards/yellow",
        json={"result": "ok", "data": {}},
    )

    assert (
        await handler.async_set_yellow_settings(
            menuai, {"disk_led": True, "heartbeat_led": True, "power_led": True}
        )
        == {}
    )
    assert aioclient_mock.call_count == 1


@pytest.mark.usefixtures("menuaiio_stubs")
async def test_send_command_invalid_command(menuai: menuai) -> None:
    """Test send command fails when command is invalid."""
    menuaiio: menuaiIO = menuai.data["menuaiio"]
    with pytest.raises(menuaiioAPIError):
        # absolute path
        await menuaiio.send_command("/test/../bad")
    with pytest.raises(menuaiioAPIError):
        # relative path
        await menuaiio.send_command("test/../bad")
    with pytest.raises(menuaiioAPIError):
        # relative path with percent encoding
        await menuaiio.send_command("test/%2E%2E/bad")
