"""Test the Ituran device_tracker."""

from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
from pyituran.exceptions import IturanApiError
from syrupy.assertion import SnapshotAssertion

from menuai.components.ituran.const import UPDATE_INTERVAL
from menuai.const import STATE_UNAVAILABLE, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform


async def test_device_tracker(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_ituran: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test state of device_tracker."""
    with patch("menuai.components.ituran.PLATFORMS", [Platform.DEVICE_TRACKER]):
        await setup_integration(menuai, mock_config_entry)
    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_availability(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    mock_ituran: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test device is marked as unavailable when we can't reach the Ituran service."""
    entity_id = "device_tracker.mock_model"
    await setup_integration(menuai, mock_config_entry)

    state = menuai.states.get(entity_id)
    assert state
    assert state.state != STATE_UNAVAILABLE

    mock_ituran.get_vehicles.side_effect = IturanApiError
    freezer.tick(UPDATE_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_UNAVAILABLE

    mock_ituran.get_vehicles.side_effect = None
    freezer.tick(UPDATE_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state
    assert state.state != STATE_UNAVAILABLE
