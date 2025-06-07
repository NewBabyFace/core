"""Tests for the Flexit Nordic (BACnet) sensor entities."""

from unittest.mock import AsyncMock

from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_with_selected_platforms

from tests.common import MockConfigEntry, snapshot_platform


async def test_sensors(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    mock_flexit_bacnet: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test sensor states are correctly collected from library."""

    await setup_with_selected_platforms(menuai, mock_config_entry, [Platform.SENSOR])

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)
