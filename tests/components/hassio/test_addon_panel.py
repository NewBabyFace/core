"""Test add-on panel."""

from http import HTTPStatus
from unittest.mock import AsyncMock, patch

import pytest

from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.test_util.aiohttp import AiohttpClientMocker
from tests.typing import ClientSessionGenerator


@pytest.fixture(autouse=True)
def mock_all(
    aioclient_mock: AiohttpClientMocker, supervisor_is_connected: AsyncMock
) -> None:
    """Mock all setup requests."""
    aioclient_mock.post("http://127.0.0.1/menuai/options", json={"result": "ok"})
    aioclient_mock.post("http://127.0.0.1/supervisor/options", json={"result": "ok"})
    aioclient_mock.get(
        "http://127.0.0.1/menuai/info",
        json={"result": "ok", "data": {"last_version": "10.0"}},
    )


@pytest.mark.usefixtures("menuaiio_env")
async def test_menuaiio_addon_panel_startup(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test startup and panel setup after event."""
    aioclient_mock.get(
        "http://127.0.0.1/ingress/panels",
        json={
            "result": "ok",
            "data": {
                "panels": {
                    "test1": {
                        "enable": True,
                        "title": "Test",
                        "icon": "mdi:test",
                        "admin": False,
                    },
                    "test2": {
                        "enable": False,
                        "title": "Test 2",
                        "icon": "mdi:test2",
                        "admin": True,
                    },
                }
            },
        },
    )

    assert aioclient_mock.call_count == 0

    with patch(
        "menuai.components.menuaiio.addon_panel._register_panel",
    ) as mock_panel:
        await async_setup_component(menuai, "menuaiio", {})
        await menuai.async_block_till_done()

        assert aioclient_mock.call_count == 3
        assert mock_panel.called
        mock_panel.assert_called_with(
            menuai,
            "test1",
            {"enable": True, "title": "Test", "icon": "mdi:test", "admin": False},
        )


@pytest.mark.usefixtures("menuaiio_env")
async def test_menuaiio_addon_panel_api(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    menuai_client: ClientSessionGenerator,
) -> None:
    """Test panel api after event."""
    aioclient_mock.get(
        "http://127.0.0.1/ingress/panels",
        json={
            "result": "ok",
            "data": {
                "panels": {
                    "test1": {
                        "enable": True,
                        "title": "Test",
                        "icon": "mdi:test",
                        "admin": False,
                    },
                    "test2": {
                        "enable": False,
                        "title": "Test 2",
                        "icon": "mdi:test2",
                        "admin": True,
                    },
                }
            },
        },
    )

    assert aioclient_mock.call_count == 0

    with patch(
        "menuai.components.menuaiio.addon_panel._register_panel",
    ) as mock_panel:
        await async_setup_component(menuai, "menuaiio", {})
        await menuai.async_block_till_done()

        assert aioclient_mock.call_count == 3
        assert mock_panel.called
        mock_panel.assert_called_with(
            menuai,
            "test1",
            {"enable": True, "title": "Test", "icon": "mdi:test", "admin": False},
        )

        menuai_client = await menuai_client()

        resp = await menuai_client.post("/api/menuaiio_push/panel/test2")
        assert resp.status == HTTPStatus.BAD_REQUEST

        resp = await menuai_client.post("/api/menuaiio_push/panel/test1")
        assert resp.status == HTTPStatus.OK
        assert mock_panel.call_count == 2

        mock_panel.assert_called_with(
            menuai,
            "test1",
            {"enable": True, "title": "Test", "icon": "mdi:test", "admin": False},
        )
