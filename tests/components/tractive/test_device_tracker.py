"""Test the Tractive device tracker platform."""

from unittest.mock import AsyncMock, patch

from syrupy.assertion import SnapshotAssertion

from menuai.components.device_tracker import SourceType
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import init_integration

from tests.common import MockConfigEntry, snapshot_platform


async def test_device_tracker(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_tractive_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test states of the device_tracker."""
    with patch(
        "menuai.components.tractive.PLATFORMS", [Platform.DEVICE_TRACKER]
    ):
        await init_integration(menuai, mock_config_entry)

        mock_tractive_client.send_position_event(mock_config_entry)
        mock_tractive_client.send_hardware_event(mock_config_entry)
        await menuai.async_block_till_done()
    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_source_type_phone(
    menuai: menuai,
    mock_tractive_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the device tracker with source type phone."""
    await init_integration(menuai, mock_config_entry)

    mock_tractive_client.send_position_event(
        mock_config_entry,
        {
            "tracker_id": "device_id_123",
            "position": {
                "latlong": [22.333, 44.555],
                "accuracy": 99,
                "sensor_used": "PHONE",
            },
        },
    )
    mock_tractive_client.send_hardware_event(mock_config_entry)
    await menuai.async_block_till_done()

    assert (
        menuai.states.get("device_tracker.test_pet_tracker").attributes["source_type"]
        is SourceType.BLUETOOTH
    )


async def test_source_type_gps(
    menuai: menuai,
    mock_tractive_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test if the source type is GPS when the location sensor is KNOWN WIFI."""
    await init_integration(menuai, mock_config_entry)

    mock_tractive_client.send_position_event(
        mock_config_entry,
        {
            "tracker_id": "device_id_123",
            "position": {
                "latlong": [22.333, 44.555],
                "accuracy": 99,
                "sensor_used": "KNOWN_WIFI",
            },
        },
    )
    mock_tractive_client.send_hardware_event(mock_config_entry)
    await menuai.async_block_till_done()

    assert (
        menuai.states.get("device_tracker.test_pet_tracker").attributes["source_type"]
        is SourceType.GPS
    )
