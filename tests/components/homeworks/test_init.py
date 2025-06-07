"""Tests for the Lutron Homeworks Series 4 and 8 integration."""

from unittest.mock import ANY, MagicMock

from pyhomeworks import exceptions as hw_exceptions
from pyhomeworks.pyhomeworks import (
    HW_BUTTON_PRESSED,
    HW_BUTTON_RELEASED,
    HW_LOGIN_INCORRECT,
)
import pytest

from menuai.components.homeworks import EVENT_BUTTON_PRESS, EVENT_BUTTON_RELEASE
from menuai.components.homeworks.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import EVENT_menuai_STOP
from menuai.core import menuai
from menuai.exceptions import ServiceValidationError

from tests.common import MockConfigEntry, async_capture_events


async def test_load_unload_config_entry(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_homeworks: MagicMock,
) -> None:
    """Test the Homeworks configuration entry loading/unloading."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    mock_homeworks.assert_called_once_with("192.168.0.1", 1234, ANY, None, None)

    await menuai.config_entries.async_unload(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert not menuai.data.get(DOMAIN)
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_load_config_entry_with_credentials(
    menuai: menuai,
    mock_config_entry_username_password: MockConfigEntry,
    mock_homeworks: MagicMock,
) -> None:
    """Test the Homeworks configuration entry loading/unloading."""
    mock_config_entry_username_password.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry_username_password.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry_username_password.state is ConfigEntryState.LOADED
    mock_homeworks.assert_called_once_with(
        "192.168.0.1", 1234, ANY, "username", "hunter2"
    )

    await menuai.config_entries.async_unload(mock_config_entry_username_password.entry_id)
    await menuai.async_block_till_done()

    assert not menuai.data.get(DOMAIN)
    assert mock_config_entry_username_password.state is ConfigEntryState.NOT_LOADED


async def test_controller_credentials_changed(
    menuai: menuai,
    mock_config_entry_username_password: MockConfigEntry,
    mock_homeworks: MagicMock,
) -> None:
    """Test controller credentials changed.

    Note: This just ensures we don't blow up when credentials changed, in the future a
    reauth flow should be added.
    """
    mock_config_entry_username_password.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry_username_password.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry_username_password.state is ConfigEntryState.LOADED
    mock_homeworks.assert_called_once_with(
        "192.168.0.1", 1234, ANY, "username", "hunter2"
    )
    hw_callback = mock_homeworks.mock_calls[0][1][2]

    hw_callback(HW_LOGIN_INCORRECT, [])


async def test_config_entry_not_ready(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_homeworks: MagicMock,
) -> None:
    """Test the Homeworks configuration entry not ready."""
    mock_homeworks.return_value.connect.side_effect = (
        hw_exceptions.HomeworksConnectionFailed
    )

    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    mock_homeworks.assert_called_once()
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_keypad_events(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_homeworks: MagicMock,
) -> None:
    """Test Homeworks keypad events."""
    release_events = async_capture_events(menuai, EVENT_BUTTON_RELEASE)
    press_events = async_capture_events(menuai, EVENT_BUTTON_PRESS)
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    mock_homeworks.assert_called_once_with("192.168.0.1", 1234, ANY, None, None)
    hw_callback = mock_homeworks.mock_calls[0][1][2]

    hw_callback(HW_BUTTON_PRESSED, ["[02:08:02:01]", 1])
    await menuai.async_block_till_done()
    assert len(press_events) == 1
    assert len(release_events) == 0
    assert press_events[0].data == {
        "id": "foyer_keypad",
        "name": "Foyer Keypad",
        "button": 1,
    }
    assert press_events[0].event_type == "homeworks_button_press"

    hw_callback(HW_BUTTON_RELEASED, ["[02:08:02:01]", 1])
    await menuai.async_block_till_done()
    assert len(press_events) == 1
    assert len(release_events) == 1
    assert release_events[0].data == {
        "id": "foyer_keypad",
        "name": "Foyer Keypad",
        "button": 1,
    }
    assert release_events[0].event_type == "homeworks_button_release"

    hw_callback("unsupported", ["[02:08:02:01]", 1])
    await menuai.async_block_till_done()
    assert len(press_events) == 1
    assert len(release_events) == 1


async def test_send_command(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_homeworks: MagicMock,
) -> None:
    """Test the send command service."""
    mock_controller = MagicMock()
    mock_homeworks.return_value = mock_controller

    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    mock_controller._send.reset_mock()
    await menuai.services.async_call(
        DOMAIN,
        "send_command",
        {"controller_id": "main_controller", "command": "KBP, [02:08:02:01], 1"},
        blocking=True,
    )
    assert len(mock_controller._send.mock_calls) == 1
    assert mock_controller._send.mock_calls[0][1] == ("KBP, [02:08:02:01], 1",)

    mock_controller._send.reset_mock()
    await menuai.services.async_call(
        DOMAIN,
        "send_command",
        {
            "controller_id": "main_controller",
            "command": [
                "KBP, [02:08:02:01], 1",
                "KBH, [02:08:02:01], 1",
                "KBR, [02:08:02:01], 1",
            ],
        },
        blocking=True,
    )
    assert len(mock_controller._send.mock_calls) == 3
    assert mock_controller._send.mock_calls[0][1] == ("KBP, [02:08:02:01], 1",)
    assert mock_controller._send.mock_calls[1][1] == ("KBH, [02:08:02:01], 1",)
    assert mock_controller._send.mock_calls[2][1] == ("KBR, [02:08:02:01], 1",)

    mock_controller._send.reset_mock()
    await menuai.services.async_call(
        DOMAIN,
        "send_command",
        {
            "controller_id": "main_controller",
            "command": [
                "KBP, [02:08:02:01], 1",
                "delay 50",
                "KBH, [02:08:02:01], 1",
                "dElAy 100",
                "KBR, [02:08:02:01], 1",
            ],
        },
        blocking=True,
    )
    assert len(mock_controller._send.mock_calls) == 3
    assert mock_controller._send.mock_calls[0][1] == ("KBP, [02:08:02:01], 1",)
    assert mock_controller._send.mock_calls[1][1] == ("KBH, [02:08:02:01], 1",)
    assert mock_controller._send.mock_calls[2][1] == ("KBR, [02:08:02:01], 1",)

    mock_controller._send.reset_mock()
    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            DOMAIN,
            "send_command",
            {"controller_id": "unknown_controller", "command": "KBP, [02:08:02:01], 1"},
            blocking=True,
        )
    assert len(mock_controller._send.mock_calls) == 0


async def test_cleanup_on_ha_shutdown(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_homeworks: MagicMock,
) -> None:
    """Test cleanup when HA shuts down."""
    mock_controller = MagicMock()
    mock_homeworks.return_value = mock_controller

    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    mock_homeworks.assert_called_once_with("192.168.0.1", 1234, ANY, None, None)
    mock_controller.stop.assert_not_called()

    menuai.bus.async_fire(EVENT_menuai_STOP)
    await menuai.async_block_till_done()

    mock_controller.stop.assert_called_once_with()
