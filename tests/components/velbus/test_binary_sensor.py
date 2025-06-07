"""Velbus binary_sensor platform tests."""

from unittest.mock import patch

from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import init_integration

from tests.common import MockConfigEntry, snapshot_platform


async def test_entities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    with patch("menuai.components.velbus.PLATFORMS", [Platform.BINARY_SENSOR]):
        await init_integration(menuai, config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, config_entry.entry_id)
