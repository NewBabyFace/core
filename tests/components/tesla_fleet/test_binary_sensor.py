"""Test the Tesla Fleet binary sensor platform."""

from unittest.mock import AsyncMock

from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion
from tesla_fleet_api.exceptions import VehicleOffline

from menuai.components.tesla_fleet.coordinator import VEHICLE_INTERVAL
from menuai.const import STATE_UNKNOWN, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import assert_entities, assert_entities_alt, setup_platform
from .const import VEHICLE_DATA_ALT

from tests.common import MockConfigEntry, async_fire_time_changed


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_binary_sensor(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    normal_config_entry: MockConfigEntry,
) -> None:
    """Tests that the binary sensor entities are correct."""

    await setup_platform(menuai, normal_config_entry, [Platform.BINARY_SENSOR])
    assert_entities(menuai, normal_config_entry.entry_id, entity_registry, snapshot)


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_binary_sensor_refresh(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    mock_vehicle_data: AsyncMock,
    freezer: FrozenDateTimeFactory,
    normal_config_entry: MockConfigEntry,
) -> None:
    """Tests that the binary sensor entities are correct."""

    await setup_platform(menuai, normal_config_entry, [Platform.BINARY_SENSOR])

    # Refresh
    mock_vehicle_data.return_value = VEHICLE_DATA_ALT
    freezer.tick(VEHICLE_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert_entities_alt(menuai, normal_config_entry.entry_id, entity_registry, snapshot)


async def test_binary_sensor_offline(
    menuai: menuai,
    mock_vehicle_data: AsyncMock,
    normal_config_entry: MockConfigEntry,
) -> None:
    """Tests that the binary sensor entities are correct when offline."""

    mock_vehicle_data.side_effect = VehicleOffline
    await setup_platform(menuai, normal_config_entry, [Platform.BINARY_SENSOR])
    state = menuai.states.get("binary_sensor.test_status")
    assert state.state == STATE_UNKNOWN
