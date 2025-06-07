"""Test the Immich sensor platform."""

from unittest.mock import Mock, patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, snapshot_platform


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensors(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_immich: Mock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the Immich sensor platform."""

    with patch("menuai.components.immich.PLATFORMS", [Platform.SENSOR]):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_admin_sensors(
    menuai: menuai,
    mock_non_admin_immich: Mock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the integration doesn't create admin sensors if not admin."""

    await setup_integration(menuai, mock_config_entry)

    assert menuai.states.get("sensor.mock_title_photos_count") is None
    assert menuai.states.get("sensor.mock_title_videos_count") is None
    assert menuai.states.get("sensor.mock_title_disk_used_by_photos") is None
    assert menuai.states.get("sensor.mock_title_disk_used_by_videos") is None
