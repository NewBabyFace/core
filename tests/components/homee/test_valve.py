"""Test Homee valves."""

from unittest.mock import MagicMock, patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.valve import (
    DOMAIN as VALVE_DOMAIN,
    SERVICE_SET_VALVE_POSITION,
    STATE_CLOSED,
    STATE_CLOSING,
    STATE_OPEN,
    STATE_OPENING,
    ValveEntityFeature,
)
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import build_mock_node, setup_integration

from tests.common import MockConfigEntry, snapshot_platform


async def test_valve_set_position(
    menuai: menuai,
    mock_homee: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test set valve position service."""
    mock_homee.nodes = [build_mock_node("valve.json")]
    mock_homee.get_node_by_id.return_value = mock_homee.nodes[0]
    await setup_integration(menuai, mock_config_entry)

    await menuai.services.async_call(
        VALVE_DOMAIN,
        SERVICE_SET_VALVE_POSITION,
        {ATTR_ENTITY_ID: "valve.test_valve_valve_position", "position": 100},
    )
    mock_homee.set_value.assert_called_once_with(1, 1, 100)


@pytest.mark.parametrize(
    ("current_value", "target_value", "state"),
    [
        (0.0, 0.0, STATE_CLOSED),
        (0.0, 100.0, STATE_OPENING),
        (100.0, 0.0, STATE_CLOSING),
        (100.0, 100.0, STATE_OPEN),
    ],
)
async def test_opening_closing(
    menuai: menuai,
    mock_homee: MagicMock,
    mock_config_entry: MockConfigEntry,
    current_value: float,
    target_value: float,
    state: str,
) -> None:
    """Test if opening/closing is detected correctly."""
    mock_homee.nodes = [build_mock_node("valve.json")]
    mock_homee.get_node_by_id.return_value = mock_homee.nodes[0]
    await setup_integration(menuai, mock_config_entry)

    valve = mock_homee.nodes[0].attributes[0]
    valve.current_value = current_value
    valve.target_value = target_value
    valve.add_on_changed_listener.call_args_list[0][0][0](valve)
    await menuai.async_block_till_done()

    assert menuai.states.get("valve.test_valve_valve_position").state == state


async def test_supported_features(
    menuai: menuai,
    mock_homee: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test supported features."""
    mock_homee.nodes = [build_mock_node("valve.json")]
    mock_homee.get_node_by_id.return_value = mock_homee.nodes[0]
    await setup_integration(menuai, mock_config_entry)

    valve = mock_homee.nodes[0].attributes[0]
    attributes = menuai.states.get("valve.test_valve_valve_position").attributes
    assert attributes["supported_features"] == ValveEntityFeature.SET_POSITION

    valve.editable = 0
    valve.add_on_changed_listener.call_args_list[0][0][0](valve)
    await menuai.async_block_till_done()

    attributes = menuai.states.get("valve.test_valve_valve_position").attributes
    assert attributes["supported_features"] == ValveEntityFeature(0)


async def test_valve_snapshot(
    menuai: menuai,
    mock_homee: MagicMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the valve snapshots."""
    mock_homee.nodes = [build_mock_node("valve.json")]
    mock_homee.get_node_by_id.return_value = mock_homee.nodes[0]
    with patch("menuai.components.homee.PLATFORMS", [Platform.VALVE]):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)
