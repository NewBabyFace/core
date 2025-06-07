"""Tests for init of Azure DevOps."""

from unittest.mock import AsyncMock

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import (
    DEVOPS_BUILD_MISSING_DATA,
    DEVOPS_BUILD_MISSING_PROJECT_DEFINITION,
    setup_integration,
)

from tests.common import MockConfigEntry

BASE_ENTITY_ID = "sensor.testproject_ci"
SENSOR_KEYS = [
    "latest_build",
    "latest_build_id",
    "latest_build_reason",
    "latest_build_result",
    "latest_build_source_branch",
    "latest_build_source_version",
    "latest_build_queue_time",
    "latest_build_start_time",
    "latest_build_finish_time",
    "latest_build_url",
]


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensors(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    mock_config_entry: MockConfigEntry,
    mock_devops_client: AsyncMock,
) -> None:
    """Test sensor entities."""
    assert await setup_integration(menuai, mock_config_entry)

    for sensor_key in SENSOR_KEYS:
        assert (entry := entity_registry.async_get(f"{BASE_ENTITY_ID}_{sensor_key}"))

        assert entry == snapshot(name=f"{entry.entity_id}-entry")

        assert menuai.states.get(entry.entity_id) == snapshot(
            name=f"{entry.entity_id}-state"
        )


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensors_missing_data(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    mock_config_entry: MockConfigEntry,
    mock_devops_client: AsyncMock,
) -> None:
    """Test sensor entities with missing data."""
    mock_devops_client.get_builds.return_value = [DEVOPS_BUILD_MISSING_DATA]

    assert await setup_integration(menuai, mock_config_entry)

    for sensor_key in SENSOR_KEYS:
        assert (entry := entity_registry.async_get(f"{BASE_ENTITY_ID}_{sensor_key}"))

        assert menuai.states.get(entry.entity_id) == snapshot(
            name=f"{entry.entity_id}-state-missing-data"
        )


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensors_missing_project_definition(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_config_entry: MockConfigEntry,
    mock_devops_client: AsyncMock,
) -> None:
    """Test sensor entities with missing project and definition."""
    mock_devops_client.get_builds.return_value = [
        DEVOPS_BUILD_MISSING_PROJECT_DEFINITION
    ]

    assert await setup_integration(menuai, mock_config_entry)

    for sensor_key in SENSOR_KEYS:
        assert not entity_registry.async_get(f"{BASE_ENTITY_ID}_{sensor_key}")
