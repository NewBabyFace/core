"""Tests for the Android TV Remote integration."""

from collections.abc import Callable
from unittest.mock import AsyncMock, MagicMock

from androidtvremote2 import CannotConnect, InvalidAuth

from menuai.config_entries import ConfigEntryState
from menuai.const import EVENT_menuai_STOP
from menuai.core import menuai

from tests.common import MockConfigEntry


async def test_load_unload_config_entry(
    menuai: menuai, mock_config_entry: MockConfigEntry, mock_api: MagicMock
) -> None:
    """Test the Android TV Remote configuration entry loading/unloading."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert mock_api.async_connect.call_count == 1
    assert mock_api.keep_reconnecting.call_count == 1

    await menuai.config_entries.async_unload(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
    assert mock_api.disconnect.call_count == 1


async def test_config_entry_not_ready(
    menuai: menuai, mock_config_entry: MockConfigEntry, mock_api: MagicMock
) -> None:
    """Test the Android TV Remote configuration entry not ready."""
    mock_api.async_connect = AsyncMock(side_effect=CannotConnect())

    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY
    assert mock_api.async_connect.call_count == 1
    assert mock_api.keep_reconnecting.call_count == 0


async def test_config_entry_reauth_at_setup(
    menuai: menuai, mock_config_entry: MockConfigEntry, mock_api: MagicMock
) -> None:
    """Test the Android TV Remote configuration entry needs reauth at setup."""
    mock_api.async_connect = AsyncMock(side_effect=InvalidAuth())

    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR
    assert any(mock_config_entry.async_get_active_flows(menuai, {"reauth"}))
    assert mock_api.async_connect.call_count == 1
    assert mock_api.keep_reconnecting.call_count == 0


async def test_config_entry_reauth_while_reconnecting(
    menuai: menuai, mock_config_entry: MockConfigEntry, mock_api: MagicMock
) -> None:
    """Test the Android TV Remote configuration entry needs reauth while reconnecting."""
    invalid_auth_callback: Callable | None = None

    def mocked_keep_reconnecting(callback: Callable):
        nonlocal invalid_auth_callback
        invalid_auth_callback = callback

    mock_api.keep_reconnecting.side_effect = mocked_keep_reconnecting

    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert not any(mock_config_entry.async_get_active_flows(menuai, {"reauth"}))
    assert mock_api.async_connect.call_count == 1
    assert mock_api.keep_reconnecting.call_count == 1

    assert invalid_auth_callback is not None
    invalid_auth_callback()
    await menuai.async_block_till_done()
    assert any(mock_config_entry.async_get_active_flows(menuai, {"reauth"}))


async def test_disconnect_on_stop(
    menuai: menuai, mock_config_entry: MockConfigEntry, mock_api: MagicMock
) -> None:
    """Test we close the connection with the Android TV when MenuAIs stops."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert mock_api.async_connect.call_count == 1
    assert mock_api.keep_reconnecting.call_count == 1

    menuai.bus.async_fire(EVENT_menuai_STOP)
    await menuai.async_block_till_done()

    assert mock_api.disconnect.call_count == 1
