"""Test for the switchbot_cloud bot as a button."""

from unittest.mock import patch

from switchbot_api import BotCommands, Device

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.components.switchbot_cloud import SwitchBotAPI
from menuai.config_entries import ConfigEntryState
from menuai.const import ATTR_ENTITY_ID, STATE_UNKNOWN
from menuai.core import menuai

from . import configure_integration


async def test_pressmode_bot(
    menuai: menuai, mock_list_devices, mock_get_status
) -> None:
    """Test press."""
    mock_list_devices.return_value = [
        Device(
            version="V1.0",
            deviceId="bot-id-1",
            deviceName="bot-1",
            deviceType="Bot",
            hubDeviceId="test-hub-id",
        ),
    ]

    mock_get_status.return_value = {"deviceMode": "pressMode"}

    entry = await configure_integration(menuai)
    assert entry.state is ConfigEntryState.LOADED

    entity_id = "button.bot_1"
    assert menuai.states.get(entity_id).state == STATE_UNKNOWN

    with patch.object(SwitchBotAPI, "send_command") as mock_send_command:
        await menuai.services.async_call(
            BUTTON_DOMAIN, SERVICE_PRESS, {ATTR_ENTITY_ID: entity_id}, blocking=True
        )
        mock_send_command.assert_called_once_with(
            "bot-id-1", BotCommands.PRESS, "command", "default"
        )

    assert menuai.states.get(entity_id).state != STATE_UNKNOWN


async def test_switchmode_bot_no_button_entity(
    menuai: menuai, mock_list_devices, mock_get_status
) -> None:
    """Test a switchMode bot isn't added as a button."""
    mock_list_devices.return_value = [
        Device(
            version="V1.0",
            deviceId="bot-id-1",
            deviceName="bot-1",
            deviceType="Bot",
            hubDeviceId="test-hub-id",
        ),
    ]

    mock_get_status.return_value = {"deviceMode": "switchMode"}

    entry = await configure_integration(menuai)
    assert entry.state is ConfigEntryState.LOADED
    assert not menuai.states.async_entity_ids(BUTTON_DOMAIN)
