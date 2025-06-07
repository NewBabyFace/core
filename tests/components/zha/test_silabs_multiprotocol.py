"""Test ZHA Silicon Labs Multiprotocol support."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import call, patch

import pytest
import zigpy.backups
import zigpy.state

from menuai.components import zha
from menuai.components.zha import silabs_multiprotocol
from menuai.components.zha.helpers import get_zha_data
from menuai.core import menuai

if TYPE_CHECKING:
    from zigpy.application import ControllerApplication


@pytest.fixture(autouse=True)
def required_platform_only():
    """Only set up the required and required base platforms to speed up tests."""
    with patch("menuai.components.zha.PLATFORMS", ()):
        yield


async def test_async_get_channel_active(menuai: menuai, setup_zha) -> None:
    """Test reading channel with an active ZHA installation."""
    await setup_zha()

    assert await silabs_multiprotocol.async_get_channel(menuai) == 15


async def test_async_get_channel_missing(
    menuai: menuai, setup_zha, zigpy_app_controller: ControllerApplication
) -> None:
    """Test reading channel with an inactive ZHA installation, no valid channel."""
    await setup_zha()

    await zha.async_unload_entry(menuai, get_zha_data(menuai).config_entry)

    # Network settings were never loaded for whatever reason
    zigpy_app_controller.state.network_info = zigpy.state.NetworkInfo()
    zigpy_app_controller.state.node_info = zigpy.state.NodeInfo()

    assert await silabs_multiprotocol.async_get_channel(menuai) is None


async def test_async_get_channel_no_zha(menuai: menuai) -> None:
    """Test reading channel with no ZHA config entries and no database."""
    assert await silabs_multiprotocol.async_get_channel(menuai) is None


async def test_async_using_multipan_active(menuai: menuai, setup_zha) -> None:
    """Test async_using_multipan with an active ZHA installation."""
    await setup_zha()

    assert await silabs_multiprotocol.async_using_multipan(menuai) is False


async def test_async_using_multipan_no_zha(menuai: menuai) -> None:
    """Test async_using_multipan with no ZHA config entries and no database."""
    assert await silabs_multiprotocol.async_using_multipan(menuai) is False


async def test_change_channel(
    menuai: menuai, setup_zha, zigpy_app_controller: ControllerApplication
) -> None:
    """Test changing the channel."""
    await setup_zha()

    task = await silabs_multiprotocol.async_change_channel(menuai, 20)
    await task

    assert zigpy_app_controller.move_network_to_channel.mock_calls == [call(20)]


async def test_change_channel_no_zha(
    menuai: menuai, zigpy_app_controller: ControllerApplication
) -> None:
    """Test changing the channel with no ZHA config entries and no database."""
    task = await silabs_multiprotocol.async_change_channel(menuai, 20)
    assert task is None

    assert zigpy_app_controller.mock_calls == []


@pytest.mark.parametrize(("delay", "sleep"), [(0, 0), (5, 0), (15, 15 - 10.27)])
async def test_change_channel_delay(
    menuai: menuai,
    setup_zha,
    zigpy_app_controller: ControllerApplication,
    delay: float,
    sleep: float,
) -> None:
    """Test changing the channel with a delay."""
    await setup_zha()

    with patch(
        "menuai.components.zha.silabs_multiprotocol.asyncio.sleep", autospec=True
    ) as mock_sleep:
        task = await silabs_multiprotocol.async_change_channel(menuai, 20, delay=delay)
        await task

    assert zigpy_app_controller.move_network_to_channel.mock_calls == [call(20)]
    assert mock_sleep.mock_calls == [call(sleep)]
