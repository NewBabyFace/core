"""Tests for Bosch Alarm component."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

from bosch_alarm_mode2.const import ALARM_MEMORY_PRIORITIES
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import call_observable, setup_integration

from tests.common import MockConfigEntry, snapshot_platform


@pytest.fixture(autouse=True)
async def platforms() -> AsyncGenerator[None]:
    """Return the platforms to be loaded for this test."""
    with patch("menuai.components.bosch_alarm.PLATFORMS", [Platform.SENSOR]):
        yield


async def test_sensor(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_panel: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the sensor state."""
    await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_faulting_points(
    menuai: menuai,
    mock_panel: AsyncMock,
    area: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that area faulting point count changes after arming the panel."""
    await setup_integration(menuai, mock_config_entry)
    entity_id = "sensor.area1_faulting_points"
    assert menuai.states.get(entity_id).state == "0"

    area.faults = 1
    await call_observable(menuai, area.ready_observer)
    assert menuai.states.get(entity_id).state == "1"


async def test_alarm_faults(
    menuai: menuai,
    mock_panel: AsyncMock,
    area: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that alarm state changes after arming the panel."""
    await setup_integration(menuai, mock_config_entry)
    entity_id = "sensor.area1_fire_alarm_issues"
    assert menuai.states.get(entity_id).state == "no_issues"

    area.alarms_ids = [ALARM_MEMORY_PRIORITIES.FIRE_TROUBLE]
    await call_observable(menuai, area.alarm_observer)

    assert menuai.states.get(entity_id).state == "trouble"
