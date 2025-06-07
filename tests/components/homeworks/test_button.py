"""Tests for the Lutron Homeworks Series 4 and 8 button."""

from unittest.mock import MagicMock

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai

from tests.common import MockConfigEntry


async def test_button_service_calls(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_homeworks: MagicMock,
) -> None:
    """Test Homeworks button service call."""
    entity_id = "button.foyer_keypad_morning"
    mock_controller = MagicMock()
    mock_homeworks.return_value = mock_controller

    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert entity_id in menuai.states.async_entity_ids(BUTTON_DOMAIN)

    mock_controller._send.reset_mock()
    await menuai.services.async_call(
        BUTTON_DOMAIN, SERVICE_PRESS, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    assert len(mock_controller._send.mock_calls) == 1
    assert mock_controller._send.mock_calls[0][1] == ("KBP, [02:08:02:01], 1",)


async def test_button_service_calls_delay(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_homeworks: MagicMock,
) -> None:
    """Test Homeworks button service call."""
    entity_id = "button.foyer_keypad_dim_up"
    mock_controller = MagicMock()
    mock_homeworks.return_value = mock_controller

    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert entity_id in menuai.states.async_entity_ids(BUTTON_DOMAIN)

    mock_controller._send.reset_mock()
    await menuai.services.async_call(
        BUTTON_DOMAIN, SERVICE_PRESS, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    assert len(mock_controller._send.mock_calls) == 2
    assert mock_controller._send.mock_calls[0][1] == ("KBP, [02:08:02:01], 3",)
    assert mock_controller._send.mock_calls[1][1] == ("KBR, [02:08:02:01], 3",)
