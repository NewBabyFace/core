"""Tests for the Jellyfin remote platform."""

from unittest.mock import MagicMock

from menuai.components.remote import (
    ATTR_COMMAND,
    ATTR_DELAY_SECS,
    ATTR_HOLD_SECS,
    ATTR_NUM_REPEATS,
    DOMAIN as R_DOMAIN,
    SERVICE_SEND_COMMAND,
)
from menuai.const import ATTR_ENTITY_ID, STATE_ON
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er

from tests.common import MockConfigEntry


async def test_remote(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    init_integration: MockConfigEntry,
    mock_jellyfin: MagicMock,
    mock_api: MagicMock,
) -> None:
    """Test the Jellyfin remote."""
    state = menuai.states.get("remote.jellyfin_device")
    state2 = menuai.states.get("remote.jellyfin_device_two")
    state3 = menuai.states.get("remote.jellyfin_device_three")
    state4 = menuai.states.get("remote.jellyfin_device_four")

    assert state
    assert state2
    # Doesn't support remote control; remote not created
    assert state3 is None
    assert state4

    assert state.state == STATE_ON


async def test_services(
    menuai: menuai,
    init_integration: MockConfigEntry,
    mock_jellyfin: MagicMock,
    mock_api: MagicMock,
) -> None:
    """Test Jellyfin remote services."""
    state = menuai.states.get("remote.jellyfin_device")
    assert state

    command = "Select"
    await menuai.services.async_call(
        R_DOMAIN,
        SERVICE_SEND_COMMAND,
        {
            ATTR_ENTITY_ID: state.entity_id,
            ATTR_COMMAND: command,
            ATTR_NUM_REPEATS: 1,
            ATTR_DELAY_SECS: 0,
            ATTR_HOLD_SECS: 0,
        },
        blocking=True,
    )
    assert len(mock_api.command.mock_calls) == 1
    assert mock_api.command.mock_calls[0].args == (
        "SESSION-UUID",
        command,
    )

    command = "MoveLeft"
    await menuai.services.async_call(
        R_DOMAIN,
        SERVICE_SEND_COMMAND,
        {
            ATTR_ENTITY_ID: state.entity_id,
            ATTR_COMMAND: command,
            ATTR_NUM_REPEATS: 2,
            ATTR_DELAY_SECS: 0,
            ATTR_HOLD_SECS: 0,
        },
        blocking=True,
    )
    assert len(mock_api.command.mock_calls) == 3
    assert mock_api.command.mock_calls[1].args == (
        "SESSION-UUID",
        command,
    )
    assert mock_api.command.mock_calls[2].args == (
        "SESSION-UUID",
        command,
    )
