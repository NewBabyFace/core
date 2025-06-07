"""Tests for the Remote Python Debugger integration."""

from unittest.mock import patch

import pytest

from menuai.components.debugpy import (
    CONF_HOST,
    CONF_PORT,
    CONF_START,
    CONF_WAIT,
    DOMAIN,
    SERVICE_START,
)
from menuai.core import menuai
from menuai.setup import async_setup_component


@pytest.fixture
def mock_debugpy():
    """Mock debugpy lib."""
    with patch("menuai.components.debugpy.debugpy") as mocked_debugpy:
        yield mocked_debugpy


async def test_default(menuai: menuai, mock_debugpy) -> None:
    """Test if the default settings work."""
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})

    mock_debugpy.listen.assert_called_once_with(("0.0.0.0", 5678))
    mock_debugpy.wait_for_client.assert_not_called()
    assert len(mock_debugpy.method_calls) == 1


async def test_wait_on_startup(menuai: menuai, mock_debugpy) -> None:
    """Test if the waiting for client is called."""
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {CONF_WAIT: True}})

    mock_debugpy.listen.assert_called_once_with(("0.0.0.0", 5678))
    mock_debugpy.wait_for_client.assert_called_once()
    assert len(mock_debugpy.method_calls) == 2


async def test_on_demand(menuai: menuai, mock_debugpy) -> None:
    """Test on-demand debugging using a service call."""
    assert await async_setup_component(
        menuai,
        DOMAIN,
        {DOMAIN: {CONF_START: False, CONF_HOST: "127.0.0.1", CONF_PORT: 80}},
    )

    mock_debugpy.listen.assert_not_called()
    mock_debugpy.wait_for_client.assert_not_called()
    assert len(mock_debugpy.method_calls) == 0

    await menuai.services.async_call(
        DOMAIN,
        SERVICE_START,
        blocking=True,
    )

    mock_debugpy.listen.assert_called_once_with(("127.0.0.1", 80))
    mock_debugpy.wait_for_client.assert_not_called()
    assert len(mock_debugpy.method_calls) == 1
