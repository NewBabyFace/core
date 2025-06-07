"""The tests for the Ring button platform."""

from unittest.mock import Mock

from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .common import MockConfigEntry, setup_platform

from tests.common import snapshot_platform


async def test_states(
    menuai: menuai,
    mock_ring_client: Mock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test states."""
    mock_config_entry.add_to_menuai(menuai)
    await setup_platform(menuai, Platform.BUTTON)
    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_button_opens_door(
    menuai: menuai,
    mock_ring_client,
    mock_ring_devices,
) -> None:
    """Tests the door open button works correctly."""
    await setup_platform(menuai, Platform.BUTTON)

    mock_intercom = mock_ring_devices.get_device(185036587)
    mock_intercom.async_open_door.assert_not_called()

    await menuai.services.async_call(
        "button", "press", {"entity_id": "button.ingress_open_door"}, blocking=True
    )

    await menuai.async_block_till_done(wait_background_tasks=True)
    mock_intercom.async_open_door.assert_called_once()
