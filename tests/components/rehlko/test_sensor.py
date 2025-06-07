"""Tests for the Rehlko sensors."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.rehlko.coordinator import SCAN_INTERVAL_MINUTES
from menuai.const import STATE_UNAVAILABLE, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform


@pytest.fixture(name="platform_sensor", autouse=True)
async def platform_sensor_fixture():
    """Patch Rehlko to only load Sensor platform."""
    with patch("menuai.components.rehlko.PLATFORMS", [Platform.SENSOR]):
        yield


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensors(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    rehlko_config_entry: MockConfigEntry,
    load_rehlko_config_entry: None,
) -> None:
    """Test the Rehlko sensors."""
    await snapshot_platform(
        menuai, entity_registry, snapshot, rehlko_config_entry.entry_id
    )


async def test_sensor_availability_device_disconnect(
    menuai: menuai,
    generator: dict[str, Any],
    mock_rehlko: AsyncMock,
    load_rehlko_config_entry: None,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test the Rehlko sensor availability when device is disconnected."""
    state = menuai.states.get("sensor.generator_1_battery_voltage")
    assert state
    assert state.state == "13.9"

    generator["device"]["isConnected"] = False

    # Move time to next update
    freezer.tick(SCAN_INTERVAL_MINUTES)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.generator_1_battery_voltage")
    assert state
    assert state.state == STATE_UNAVAILABLE


async def test_sensor_availability_poll_failure(
    menuai: menuai,
    mock_rehlko: AsyncMock,
    load_rehlko_config_entry: None,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test the Rehlko sensor availability when cloud poll fails."""
    state = menuai.states.get("sensor.generator_1_battery_voltage")
    assert state
    assert state.state == "13.9"

    mock_rehlko.get_generator_data.side_effect = Exception("Test exception")

    # Move time to next update
    freezer.tick(SCAN_INTERVAL_MINUTES)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.generator_1_battery_voltage")
    assert state
    assert state.state == STATE_UNAVAILABLE
