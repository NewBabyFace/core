"""Test the switch functionality."""

from unittest.mock import MagicMock

from pyegps.exceptions import EgpsException
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.menuai import (
    DOMAIN as HOME_ASSISTANT_DOMAIN,
    SERVICE_UPDATE_ENTITY,
)
from menuai.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from menuai.config_entries import ConfigEntryState
from menuai.const import STATE_OFF, STATE_ON
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry


async def _test_switch_on_off(
    menuai: menuai, entity_id: str, dev: MagicMock
) -> None:
    """Call switch on/off service."""
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {"entity_id": entity_id},
        blocking=True,
    )
    assert menuai.states.get(entity_id).state == STATE_ON

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {"entity_id": entity_id},
        blocking=True,
    )

    assert menuai.states.get(entity_id).state == STATE_OFF


async def _test_switch_on_exeception(
    menuai: menuai, entity_id: str, dev: MagicMock
) -> None:
    """Call switch on service with USBError side effect."""
    dev.switch_on.side_effect = EgpsException
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            HOME_ASSISTANT_DOMAIN,
            SERVICE_TURN_ON,
            {"entity_id": entity_id},
            blocking=True,
        )
    dev.switch_on.side_effect = None


async def _test_switch_off_exeception(
    menuai: menuai, entity_id: str, dev: MagicMock
) -> None:
    """Call switch off service with USBError side effect."""
    dev.switch_off.side_effect = EgpsException
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {"entity_id": entity_id},
            blocking=True,
        )
    dev.switch_off.side_effect = None


async def _test_switch_update_exception(
    menuai: menuai, entity_id: str, dev: MagicMock
) -> None:
    """Call switch update with USBError side effect."""
    dev.get_status.side_effect = EgpsException
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_UPDATE_ENTITY,
            {"entity_id": entity_id},
            blocking=True,
        )
    dev.get_status.side_effect = None


@pytest.mark.parametrize(
    "entity_name",
    [
        "mockedusbdevice_socket_0",
        "mockedusbdevice_socket_1",
        "mockedusbdevice_socket_2",
        "mockedusbdevice_socket_3",
    ],
)
async def test_switch_setup(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    valid_config_entry: MockConfigEntry,
    mock_get_device: MagicMock,
    entity_name: str,
    snapshot: SnapshotAssertion,
) -> None:
    """Test setup and functionality of device switches."""

    entry = valid_config_entry
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

    state = menuai.states.get(f"switch.{entity_name}")
    assert state == snapshot
    assert entity_registry.async_get(state.entity_id) == snapshot

    device_mock = mock_get_device.return_value
    await _test_switch_on_off(menuai, state.entity_id, device_mock)
    await _test_switch_on_exeception(menuai, state.entity_id, device_mock)
    await _test_switch_off_exeception(menuai, state.entity_id, device_mock)
    await _test_switch_update_exception(menuai, state.entity_id, device_mock)

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()
