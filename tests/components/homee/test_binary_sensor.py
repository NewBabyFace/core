"""Test homee binary sensors."""

from unittest.mock import MagicMock, patch

from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import build_mock_node, setup_integration

from tests.common import MockConfigEntry, snapshot_platform


async def test_sensor_snapshot(
    menuai: menuai,
    mock_homee: MagicMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the multisensor snapshot."""
    mock_homee.nodes = [build_mock_node("binary_sensors.json")]
    mock_homee.get_node_by_id.return_value = mock_homee.nodes[0]
    with patch("menuai.components.homee.PLATFORMS", [Platform.BINARY_SENSOR]):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)
