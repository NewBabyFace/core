"""Binary sensor tests for the Sabnzbd component."""

from unittest.mock import patch

from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry, snapshot_platform


@patch("menuai.components.sabnzbd.PLATFORMS", [Platform.BINARY_SENSOR])
async def test_sensor(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test binary sensor setup."""
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await snapshot_platform(menuai, entity_registry, snapshot, config_entry.entry_id)
