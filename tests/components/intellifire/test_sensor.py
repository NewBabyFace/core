"""Test IntelliFire Binary Sensors."""

from unittest.mock import AsyncMock, patch

from freezegun import freeze_time
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, snapshot_platform


@freeze_time("2021-01-01T12:00:00Z")
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_all_sensor_entities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_config_entry_current: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    mock_apis_single_fp: tuple[AsyncMock, AsyncMock, AsyncMock],
) -> None:
    """Test all entities."""

    with (
        patch("menuai.components.intellifire.PLATFORMS", [Platform.SENSOR]),
    ):
        await setup_integration(menuai, mock_config_entry_current)
        await snapshot_platform(
            menuai, entity_registry, snapshot, mock_config_entry_current.entry_id
        )
