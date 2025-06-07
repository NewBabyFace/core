"""Test the Tesla Fleet device tracker platform."""

from unittest.mock import AsyncMock

from syrupy.assertion import SnapshotAssertion
from tesla_fleet_api.exceptions import VehicleOffline

from menuai.const import STATE_UNKNOWN, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import assert_entities, setup_platform

from tests.common import MockConfigEntry


async def test_device_tracker(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    normal_config_entry: MockConfigEntry,
) -> None:
    """Tests that the device tracker entities are correct."""

    await setup_platform(menuai, normal_config_entry, [Platform.DEVICE_TRACKER])
    assert_entities(menuai, normal_config_entry.entry_id, entity_registry, snapshot)


async def test_device_tracker_offline(
    menuai: menuai,
    mock_vehicle_data: AsyncMock,
    normal_config_entry: MockConfigEntry,
) -> None:
    """Tests that the device tracker entities are correct when offline."""

    mock_vehicle_data.side_effect = VehicleOffline
    await setup_platform(menuai, normal_config_entry, [Platform.DEVICE_TRACKER])
    state = menuai.states.get("device_tracker.test_location")
    assert state.state == STATE_UNKNOWN
