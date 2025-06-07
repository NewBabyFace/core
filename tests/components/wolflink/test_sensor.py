"""Test the Wolf SmartSet Service Sensor platform."""

from unittest.mock import MagicMock

from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, patch, snapshot_platform


async def test_device_entry(
    menuai: menuai,
    mock_wolflink: MagicMock,
    mock_config_entry: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test device entry creation."""

    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    device = device_registry.async_get_device({(mock_config_entry.domain, "1234")})
    assert device == snapshot


async def test_sensors(
    menuai: menuai,
    mock_wolflink: MagicMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test wolflink sensors."""

    with patch("menuai.components.wolflink.PLATFORMS", [Platform.SENSOR]):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)
