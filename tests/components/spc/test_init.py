"""Tests for Vanderbilt SPC component."""

from unittest.mock import AsyncMock

from menuai.core import menuai
from menuai.setup import async_setup_component


async def test_valid_device_config(menuai: menuai, mock_client: AsyncMock) -> None:
    """Test valid device config."""
    config = {"spc": {"api_url": "http://localhost/", "ws_url": "ws://localhost/"}}

    assert await async_setup_component(menuai, "spc", config) is True


async def test_invalid_device_config(
    menuai: menuai, mock_client: AsyncMock
) -> None:
    """Test valid device config."""
    config = {"spc": {"api_url": "http://localhost/"}}

    assert await async_setup_component(menuai, "spc", config) is False
