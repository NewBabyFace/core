"""Tests for binary sensor platform."""

from unittest.mock import AsyncMock, patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, snapshot_platform


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_binary_sensor_snapshot(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_automower_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Snapshot test states of the binary sensors."""
    with patch(
        "menuai.components.husqvarna_automower.PLATFORMS",
        [Platform.BINARY_SENSOR],
    ):
        await setup_integration(menuai, mock_config_entry)
        await snapshot_platform(
            menuai, entity_registry, snapshot, mock_config_entry.entry_id
        )
