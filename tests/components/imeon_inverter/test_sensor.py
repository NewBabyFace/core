"""Test the Imeon Inverter sensors."""

from unittest.mock import MagicMock, patch

from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, snapshot_platform


async def test_sensors(
    menuai: menuai,
    mock_imeon_inverter: MagicMock,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the Imeon Inverter sensors."""
    with patch(
        "menuai.components.imeon_inverter.const.PLATFORMS", [Platform.SENSOR]
    ):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)
