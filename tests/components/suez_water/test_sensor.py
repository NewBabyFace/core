"""Test Suez_water sensor platform."""

from datetime import date
from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.suez_water.const import DATA_REFRESH_INTERVAL
from menuai.components.suez_water.coordinator import PySuezError
from menuai.config_entries import ConfigEntryState
from menuai.const import STATE_UNAVAILABLE, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform


async def test_sensors_valid_state(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    suez_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test that suez_water sensor is loaded and in a valid state."""
    with patch("menuai.components.suez_water.PLATFORMS", [Platform.SENSOR]):
        await setup_integration(menuai, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.LOADED
    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)

    state = menuai.states.get("sensor.suez_mock_device_water_usage_yesterday")
    assert state
    previous: dict = state.attributes["previous_month_consumption"]
    assert previous
    assert previous.get(date.fromisoformat("2024-12-01")) is None
    assert previous.get(str(date.fromisoformat("2024-12-01"))) == 154


@pytest.mark.parametrize(
    ("method", "price_on_error", "consumption_on_error"),
    [
        ("fetch_aggregated_data", STATE_UNAVAILABLE, STATE_UNAVAILABLE),
        ("get_price", STATE_UNAVAILABLE, "160"),
    ],
)
async def test_sensors_failed_update(
    menuai: menuai,
    suez_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    method: str,
    price_on_error: str,
    consumption_on_error: str,
) -> None:
    """Test that suez_water sensor reflect failure when api fails."""
    await setup_integration(menuai, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.LOADED

    entity_ids = await menuai.async_add_executor_job(menuai.states.entity_ids)
    assert len(entity_ids) == 2

    state = menuai.states.get("sensor.suez_mock_device_water_price")
    assert state.state == "4.74"
    state = menuai.states.get("sensor.suez_mock_device_water_usage_yesterday")
    assert state.state == "160"

    getattr(suez_client, method).side_effect = PySuezError("Should fail to update")

    freezer.tick(DATA_REFRESH_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(True)

    state = menuai.states.get("sensor.suez_mock_device_water_price")
    assert state.state == price_on_error
    state = menuai.states.get("sensor.suez_mock_device_water_usage_yesterday")
    assert state.state == consumption_on_error
