"""Test the Ituran device_tracker."""

from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
from pyituran.exceptions import IturanApiError
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.ituran.const import UPDATE_INTERVAL
from menuai.const import STATE_UNAVAILABLE, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensor(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_ituran: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test state of sensor."""
    with patch("menuai.components.ituran.PLATFORMS", [Platform.SENSOR]):
        await setup_integration(menuai, mock_config_entry)
    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_availability(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    mock_ituran: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test sensor is marked as unavailable when we can't reach the Ituran service."""
    entities = [
        "sensor.mock_model_address",
        "sensor.mock_model_battery_voltage",
        "sensor.mock_model_heading",
        "sensor.mock_model_last_update_from_vehicle",
        "sensor.mock_model_mileage",
        "sensor.mock_model_speed",
    ]

    await setup_integration(menuai, mock_config_entry)

    for entity_id in entities:
        state = menuai.states.get(entity_id)
        assert state
        assert state.state != STATE_UNAVAILABLE

    mock_ituran.get_vehicles.side_effect = IturanApiError
    freezer.tick(UPDATE_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    for entity_id in entities:
        state = menuai.states.get(entity_id)
        assert state
        assert state.state == STATE_UNAVAILABLE

    mock_ituran.get_vehicles.side_effect = None
    freezer.tick(UPDATE_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    for entity_id in entities:
        state = menuai.states.get(entity_id)
        assert state
        assert state.state != STATE_UNAVAILABLE
