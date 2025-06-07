"""Test the Tractive sensor platform."""

from unittest.mock import AsyncMock, patch

from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import init_integration

from tests.common import MockConfigEntry, snapshot_platform


async def test_sensor(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_tractive_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test states of the sensor."""
    with patch("menuai.components.tractive.PLATFORMS", [Platform.SENSOR]):
        await init_integration(menuai, mock_config_entry)

        mock_tractive_client.send_hardware_event(mock_config_entry)
        mock_tractive_client.send_wellness_event(mock_config_entry)
        await menuai.async_block_till_done()
    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)
