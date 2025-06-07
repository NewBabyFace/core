"""Tests the sensors provided by the Garages Amsterdam integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import snapshot_platform


async def test_all_sensors(
    menuai: menuai,
    mock_garages_amsterdam: AsyncMock,
    mock_config_entry: AsyncMock,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test all sensors."""
    with patch(
        "menuai.components.garages_amsterdam.PLATFORMS", [Platform.SENSOR]
    ):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)
