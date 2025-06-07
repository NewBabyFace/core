"""Test the Aquacell init module."""

from __future__ import annotations

from unittest.mock import AsyncMock

from syrupy.assertion import SnapshotAssertion

from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, snapshot_platform


async def test_sensors(
    menuai: menuai,
    mock_aquacell_api: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the creation of Aquacell sensors."""
    await setup_integration(menuai, mock_config_entry)
    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)
