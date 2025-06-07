"""Tests for the coordinator of the WLED integration."""

import asyncio
from collections.abc import Callable
from copy import deepcopy
from unittest.mock import MagicMock

import pytest
from wled import (
    Device as WLEDDevice,
    WLEDConnectionClosedError,
    WLEDConnectionError,
    WLEDError,
)

from menuai.components.wled.const import SCAN_INTERVAL
from menuai.const import (
    EVENT_menuai_STOP,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from menuai.core import menuai
from menuai.util import dt as dt_util

from tests.common import MockConfigEntry, async_fire_time_changed


async def test_not_supporting_websocket(
    menuai: menuai, init_integration: MockConfigEntry, mock_wled: MagicMock
) -> None:
    """Ensure no WebSocket attempt is made if non-WebSocket device."""
    assert mock_wled.connect.call_count == 0


@pytest.mark.parametrize("device_fixture", ["rgb_websocket"])
async def test_websocket_already_connected(
    menuai: menuai, init_integration: MockConfigEntry, mock_wled: MagicMock
) -> None:
    """Ensure no a second WebSocket connection is made, if already connected."""
    assert mock_wled.connect.call_count == 1

    mock_wled.connected = True
    async_fire_time_changed(menuai, dt_util.utcnow() + SCAN_INTERVAL)
    await menuai.async_block_till_done()

    assert mock_wled.connect.call_count == 1


@pytest.mark.parametrize("device_fixture", ["rgb_websocket"])
async def test_websocket_connect_error_no_listen(
    menuai: menuai,
    init_integration: MockConfigEntry,
    mock_wled: MagicMock,
) -> None:
    """Ensure we don't start listening if WebSocket connection failed."""
    assert mock_wled.connect.call_count == 1
    assert mock_wled.listen.call_count == 1

    mock_wled.connect.side_effect = WLEDConnectionError
    async_fire_time_changed(menuai, dt_util.utcnow() + SCAN_INTERVAL)
    await menuai.async_block_till_done()

    assert mock_wled.connect.call_count == 2
    assert mock_wled.listen.call_count == 1


@pytest.mark.parametrize("device_fixture", ["rgb_websocket"])
async def test_websocket(
    menuai: menuai,
    init_integration: MockConfigEntry,
    mock_wled: MagicMock,
) -> None:
    """Test WebSocket connection."""
    state = menuai.states.get("light.wled_websocket")
    assert state
    assert state.state == STATE_ON

    # There is no Future in place yet...
    assert mock_wled.connect.call_count == 1
    assert mock_wled.listen.call_count == 1
    assert mock_wled.disconnect.call_count == 1

    connection_connected = asyncio.Future()
    connection_finished = asyncio.Future()

    async def connect(callback: Callable[[WLEDDevice], None]):
        connection_connected.set_result(callback)
        await connection_finished

    # Mock out wled.listen with a Future
    mock_wled.listen.side_effect = connect

    # Mock out the event bus
    mock_bus = MagicMock()
    menuai.bus = mock_bus

    # Next refresh it should connect
    async_fire_time_changed(menuai, dt_util.utcnow() + SCAN_INTERVAL)
    callback = await connection_connected

    # Connected to WebSocket, disconnect not called
    # listening for MenuAI to stop
    assert mock_wled.connect.call_count == 2
    assert mock_wled.listen.call_count == 2
    assert mock_wled.disconnect.call_count == 1
    assert mock_bus.async_listen_once.call_count == 1
    assert (
        mock_bus.async_listen_once.call_args_list[0][0][0] == EVENT_menuai_STOP
    )
    assert (
        mock_bus.async_listen_once.call_args_list[0][0][1].__name__ == "close_websocket"
    )
    assert mock_bus.async_listen_once.return_value.call_count == 0

    # Send update from WebSocket
    updated_device = deepcopy(mock_wled.update.return_value)
    updated_device.state.on = False
    callback(updated_device)
    await menuai.async_block_till_done()

    # Check if entity updated
    state = menuai.states.get("light.wled_websocket")
    assert state
    assert state.state == STATE_OFF

    # Resolve Future with a connection losed.
    connection_finished.set_exception(WLEDConnectionClosedError)
    await menuai.async_block_till_done()

    # Disconnect called, unsubbed MenuAI stop listener
    assert mock_wled.disconnect.call_count == 2
    assert mock_bus.async_listen_once.return_value.call_count == 1

    # Light still available, as polling takes over
    state = menuai.states.get("light.wled_websocket")
    assert state
    assert state.state == STATE_OFF


@pytest.mark.parametrize("device_fixture", ["rgb_websocket"])
async def test_websocket_error(
    menuai: menuai,
    init_integration: MockConfigEntry,
    mock_wled: MagicMock,
) -> None:
    """Test WebSocket connection erroring out, marking lights unavailable."""
    state = menuai.states.get("light.wled_websocket")
    assert state
    assert state.state == STATE_ON

    connection_connected = asyncio.Future()
    connection_finished = asyncio.Future()

    async def connect(callback: Callable[[WLEDDevice], None]):
        connection_connected.set_result(None)
        await connection_finished

    mock_wled.listen.side_effect = connect
    async_fire_time_changed(menuai, dt_util.utcnow() + SCAN_INTERVAL)
    await connection_connected

    # Resolve Future with an error.
    connection_finished.set_exception(WLEDError)
    await menuai.async_block_till_done()

    # Light no longer available as an error occurred
    state = menuai.states.get("light.wled_websocket")
    assert state
    assert state.state == STATE_UNAVAILABLE


@pytest.mark.parametrize("device_fixture", ["rgb_websocket"])
async def test_websocket_disconnect_on_home_assistant_stop(
    menuai: menuai,
    init_integration: MockConfigEntry,
    mock_wled: MagicMock,
) -> None:
    """Ensure WebSocket is disconnected when MenuAI stops."""
    assert mock_wled.disconnect.call_count == 1
    connection_connected = asyncio.Future()
    connection_finished = asyncio.Future()

    async def connect(callback: Callable[[WLEDDevice], None]):
        connection_connected.set_result(None)
        await connection_finished

    mock_wled.listen.side_effect = connect
    async_fire_time_changed(menuai, dt_util.utcnow() + SCAN_INTERVAL)
    await connection_connected

    assert mock_wled.disconnect.call_count == 1

    menuai.bus.fire(EVENT_menuai_STOP)
    await menuai.async_block_till_done()
    await menuai.async_block_till_done()
    assert mock_wled.disconnect.call_count == 2
