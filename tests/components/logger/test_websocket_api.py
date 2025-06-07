"""Tests for Logger Websocket API commands."""

import logging
from unittest.mock import patch

from menuai import loader
from menuai.components.logger.helpers import DATA_LOGGER
from menuai.components.websocket_api import TYPE_RESULT
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import MockUser
from tests.typing import WebSocketGenerator


async def test_integration_log_info(
    menuai: menuai, menuai_ws_client: WebSocketGenerator, menuai_admin_user: MockUser
) -> None:
    """Test fetching integration log info."""

    assert await async_setup_component(menuai, "logger", {})

    logging.getLogger("menuai.components.http").setLevel(logging.DEBUG)
    logging.getLogger("menuai.components.websocket_api").setLevel(logging.DEBUG)

    websocket_client = await menuai_ws_client()
    await websocket_client.send_json({"id": 7, "type": "logger/log_info"})

    msg = await websocket_client.receive_json()
    assert msg["id"] == 7
    assert msg["type"] == TYPE_RESULT
    assert msg["success"]
    assert {"domain": "http", "level": logging.DEBUG} in msg["result"]


async def test_integration_log_level_logger_not_loaded(
    menuai: menuai, menuai_ws_client: WebSocketGenerator, menuai_admin_user: MockUser
) -> None:
    """Test setting integration log level."""
    websocket_client = await menuai_ws_client()
    await websocket_client.send_json(
        {
            "id": 7,
            "type": "logger/log_level",
            "integration": "websocket_api",
            "level": logging.DEBUG,
            "persistence": "none",
        }
    )

    msg = await websocket_client.receive_json()
    assert msg["id"] == 7
    assert msg["type"] == TYPE_RESULT
    assert not msg["success"]


async def test_integration_log_level(
    menuai: menuai, menuai_ws_client: WebSocketGenerator, menuai_admin_user: MockUser
) -> None:
    """Test setting integration log level."""
    websocket_client = await menuai_ws_client()
    assert await async_setup_component(menuai, "logger", {})

    await websocket_client.send_json(
        {
            "id": 7,
            "type": "logger/integration_log_level",
            "integration": "websocket_api",
            "level": "DEBUG",
            "persistence": "none",
        }
    )

    msg = await websocket_client.receive_json()
    assert msg["id"] == 7
    assert msg["type"] == TYPE_RESULT
    assert msg["success"]

    assert menuai.data[DATA_LOGGER].overrides == {
        "menuai.components.websocket_api": logging.DEBUG
    }


async def test_custom_integration_log_level(
    menuai: menuai, menuai_ws_client: WebSocketGenerator, menuai_admin_user: MockUser
) -> None:
    """Test setting integration log level."""
    websocket_client = await menuai_ws_client()
    assert await async_setup_component(menuai, "logger", {})

    integration = loader.Integration(
        menuai,
        "custom_components.hue",
        None,
        {
            "name": "Hue",
            "dependencies": [],
            "requirements": [],
            "domain": "hue",
            "loggers": ["some_other_logger"],
        },
    )

    with (
        patch(
            "menuai.components.logger.helpers.async_get_integration",
            return_value=integration,
        ),
        patch(
            "menuai.components.logger.websocket_api.async_get_integration",
            return_value=integration,
        ),
    ):
        await websocket_client.send_json(
            {
                "id": 7,
                "type": "logger/integration_log_level",
                "integration": "hue",
                "level": "DEBUG",
                "persistence": "none",
            }
        )

        msg = await websocket_client.receive_json()
        assert msg["id"] == 7
        assert msg["type"] == TYPE_RESULT
        assert msg["success"]

        assert menuai.data[DATA_LOGGER].overrides == {
            "menuai.components.hue": logging.DEBUG,
            "custom_components.hue": logging.DEBUG,
            "some_other_logger": logging.DEBUG,
        }


async def test_integration_log_level_unknown_integration(
    menuai: menuai, menuai_ws_client: WebSocketGenerator, menuai_admin_user: MockUser
) -> None:
    """Test setting integration log level for an unknown integration."""
    websocket_client = await menuai_ws_client()
    assert await async_setup_component(menuai, "logger", {})

    await websocket_client.send_json(
        {
            "id": 7,
            "type": "logger/integration_log_level",
            "integration": "websocket_api_123",
            "level": "DEBUG",
            "persistence": "none",
        }
    )

    msg = await websocket_client.receive_json()
    assert msg["id"] == 7
    assert msg["type"] == TYPE_RESULT
    assert not msg["success"]


async def test_module_log_level(
    menuai: menuai, menuai_ws_client: WebSocketGenerator, menuai_admin_user: MockUser
) -> None:
    """Test setting integration log level."""
    websocket_client = await menuai_ws_client()
    assert await async_setup_component(
        menuai,
        "logger",
        {"logger": {"logs": {"menuai.components.other_component": "warning"}}},
    )

    await websocket_client.send_json(
        {
            "id": 7,
            "type": "logger/log_level",
            "module": "menuai.components.websocket_api",
            "level": "DEBUG",
            "persistence": "none",
        }
    )

    msg = await websocket_client.receive_json()
    assert msg["id"] == 7
    assert msg["type"] == TYPE_RESULT
    assert msg["success"]

    assert menuai.data[DATA_LOGGER].overrides == {
        "menuai.components.websocket_api": logging.DEBUG,
        "menuai.components.other_component": logging.WARNING,
    }


async def test_module_log_level_override(
    menuai: menuai, menuai_ws_client: WebSocketGenerator, menuai_admin_user: MockUser
) -> None:
    """Test override yaml integration log level."""
    websocket_client = await menuai_ws_client()
    assert await async_setup_component(
        menuai,
        "logger",
        {"logger": {"logs": {"menuai.components.websocket_api": "warning"}}},
    )

    assert menuai.data[DATA_LOGGER].overrides == {
        "menuai.components.websocket_api": logging.WARNING
    }

    await websocket_client.send_json(
        {
            "id": 6,
            "type": "logger/log_level",
            "module": "menuai.components.websocket_api",
            "level": "ERROR",
            "persistence": "none",
        }
    )

    msg = await websocket_client.receive_json()
    assert msg["id"] == 6
    assert msg["type"] == TYPE_RESULT
    assert msg["success"]

    assert menuai.data[DATA_LOGGER].overrides == {
        "menuai.components.websocket_api": logging.ERROR
    }

    await websocket_client.send_json(
        {
            "id": 7,
            "type": "logger/log_level",
            "module": "menuai.components.websocket_api",
            "level": "DEBUG",
            "persistence": "none",
        }
    )

    msg = await websocket_client.receive_json()
    assert msg["id"] == 7
    assert msg["type"] == TYPE_RESULT
    assert msg["success"]

    assert menuai.data[DATA_LOGGER].overrides == {
        "menuai.components.websocket_api": logging.DEBUG
    }

    await websocket_client.send_json(
        {
            "id": 8,
            "type": "logger/log_level",
            "module": "menuai.components.websocket_api",
            "level": "NOTSET",
            "persistence": "none",
        }
    )

    msg = await websocket_client.receive_json()
    assert msg["id"] == 8
    assert msg["type"] == TYPE_RESULT
    assert msg["success"]

    assert menuai.data[DATA_LOGGER].overrides == {
        "menuai.components.websocket_api": logging.NOTSET
    }
