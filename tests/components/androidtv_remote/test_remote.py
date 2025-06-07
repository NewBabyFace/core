"""Tests for the Android TV Remote remote platform."""

from unittest.mock import MagicMock, call

from androidtvremote2 import ConnectionClosed
import pytest

from menuai.config_entries import ConfigEntryState
from menuai.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.exceptions import menuaiError

from tests.common import MockConfigEntry

REMOTE_ENTITY = "remote.my_android_tv"


async def test_remote_receives_push_updates(
    menuai: menuai, mock_config_entry: MockConfigEntry, mock_api: MagicMock
) -> None:
    """Test the Android TV Remote receives push updates and state is updated."""
    new_options = {"apps": {"com.google.android.youtube.tv": {"app_name": "YouTube"}}}
    mock_config_entry.add_to_menuai(menuai)
    menuai.config_entries.async_update_entry(mock_config_entry, options=new_options)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.LOADED

    mock_api._on_is_on_updated(False)
    assert menuai.states.is_state(REMOTE_ENTITY, STATE_OFF)

    mock_api._on_is_on_updated(True)
    assert menuai.states.is_state(REMOTE_ENTITY, STATE_ON)

    mock_api._on_current_app_updated("activity1")
    assert (
        menuai.states.get(REMOTE_ENTITY).attributes.get("current_activity") == "activity1"
    )

    mock_api._on_current_app_updated("com.google.android.youtube.tv")
    assert (
        menuai.states.get(REMOTE_ENTITY).attributes.get("current_activity") == "YouTube"
    )

    mock_api._on_is_available_updated(False)
    assert menuai.states.is_state(REMOTE_ENTITY, STATE_UNAVAILABLE)

    mock_api._on_is_available_updated(True)
    assert menuai.states.is_state(REMOTE_ENTITY, STATE_ON)


async def test_remote_toggles(
    menuai: menuai, mock_config_entry: MockConfigEntry, mock_api: MagicMock
) -> None:
    """Test the Android TV Remote toggles."""
    new_options = {"apps": {"com.google.android.youtube.tv": {"app_name": "YouTube"}}}
    mock_config_entry.add_to_menuai(menuai)
    menuai.config_entries.async_update_entry(mock_config_entry, options=new_options)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.LOADED

    await menuai.services.async_call(
        "remote",
        "turn_off",
        {"entity_id": REMOTE_ENTITY},
        blocking=True,
    )
    mock_api._on_is_on_updated(False)

    mock_api.send_key_command.assert_called_with("POWER", "SHORT")

    await menuai.services.async_call(
        "remote",
        "turn_on",
        {"entity_id": REMOTE_ENTITY},
        blocking=True,
    )
    mock_api._on_is_on_updated(True)

    mock_api.send_key_command.assert_called_with("POWER", "SHORT")
    assert mock_api.send_key_command.call_count == 2

    await menuai.services.async_call(
        "remote",
        "turn_on",
        {"entity_id": REMOTE_ENTITY, "activity": "activity1"},
        blocking=True,
    )

    mock_api.send_key_command.send_launch_app_command("activity1")
    assert mock_api.send_key_command.call_count == 2
    assert mock_api.send_launch_app_command.call_count == 1

    await menuai.services.async_call(
        "remote",
        "turn_on",
        {"entity_id": REMOTE_ENTITY, "activity": "YouTube"},
        blocking=True,
    )

    mock_api.send_key_command.send_launch_app_command("com.google.android.youtube.tv")
    assert mock_api.send_key_command.call_count == 2
    assert mock_api.send_launch_app_command.call_count == 2


async def test_remote_send_command(
    menuai: menuai, mock_config_entry: MockConfigEntry, mock_api: MagicMock
) -> None:
    """Test remote.send_command service."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.LOADED

    await menuai.services.async_call(
        "remote",
        "send_command",
        {
            "entity_id": REMOTE_ENTITY,
            "command": "DPAD_LEFT",
            "num_repeats": 2,
            "delay_secs": 0.01,
        },
        blocking=True,
    )
    mock_api.send_key_command.assert_called_with("DPAD_LEFT", "SHORT")
    assert mock_api.send_key_command.call_count == 2


async def test_remote_send_command_multiple(
    menuai: menuai, mock_config_entry: MockConfigEntry, mock_api: MagicMock
) -> None:
    """Test remote.send_command service with multiple commands."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.LOADED

    await menuai.services.async_call(
        "remote",
        "send_command",
        {
            "entity_id": REMOTE_ENTITY,
            "command": ["DPAD_LEFT", "DPAD_UP"],
            "delay_secs": 0.01,
        },
        blocking=True,
    )
    assert mock_api.send_key_command.mock_calls == [
        call("DPAD_LEFT", "SHORT"),
        call("DPAD_UP", "SHORT"),
    ]


async def test_remote_send_command_with_hold_secs(
    menuai: menuai, mock_config_entry: MockConfigEntry, mock_api: MagicMock
) -> None:
    """Test remote.send_command service with hold_secs."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.LOADED

    await menuai.services.async_call(
        "remote",
        "send_command",
        {
            "entity_id": REMOTE_ENTITY,
            "command": "DPAD_RIGHT",
            "delay_secs": 0.01,
            "hold_secs": 0.01,
        },
        blocking=True,
    )
    assert mock_api.send_key_command.mock_calls == [
        call("DPAD_RIGHT", "START_LONG"),
        call("DPAD_RIGHT", "END_LONG"),
    ]


async def test_remote_connection_closed(
    menuai: menuai, mock_config_entry: MockConfigEntry, mock_api: MagicMock
) -> None:
    """Test commands raise menuaiError if ConnectionClosed."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.LOADED

    mock_api.send_key_command.side_effect = ConnectionClosed()
    with pytest.raises(
        menuaiError, match="Connection to the Android TV device is closed"
    ):
        await menuai.services.async_call(
            "remote",
            "send_command",
            {
                "entity_id": REMOTE_ENTITY,
                "command": "DPAD_LEFT",
                "delay_secs": 0.01,
            },
            blocking=True,
        )
    assert mock_api.send_key_command.mock_calls == [call("DPAD_LEFT", "SHORT")]

    mock_api.send_launch_app_command.side_effect = ConnectionClosed()
    with pytest.raises(
        menuaiError, match="Connection to the Android TV device is closed"
    ):
        await menuai.services.async_call(
            "remote",
            "turn_on",
            {"entity_id": REMOTE_ENTITY, "activity": "activity1"},
            blocking=True,
        )
    assert mock_api.send_launch_app_command.mock_calls == [call("activity1")]
