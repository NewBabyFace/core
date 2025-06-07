"""Tests for the device tracker platform."""

from unittest.mock import AsyncMock, patch

from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, snapshot_platform


async def test_device_tracker_snapshot(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_automower_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Snapshot test of the device tracker."""
    with patch(
        "menuai.components.husqvarna_automower.PLATFORMS",
        [Platform.DEVICE_TRACKER],
    ):
        await setup_integration(menuai, mock_config_entry)
        await snapshot_platform(
            menuai, entity_registry, snapshot, mock_config_entry.entry_id
        )
