"""Test Homee buttons."""

from unittest.mock import MagicMock, patch

from syrupy.assertion import SnapshotAssertion

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import build_mock_node, setup_integration

from tests.common import MockConfigEntry, snapshot_platform


async def test_button_press(
    menuai: menuai,
    mock_homee: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test press button service."""
    mock_homee.nodes = [build_mock_node("buttons.json")]
    mock_homee.get_node_by_id.return_value = mock_homee.nodes[0]
    await setup_integration(menuai, mock_config_entry)

    await menuai.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: "button.test_button_impulse_1"},
        blocking=True,
    )

    mock_homee.set_value.assert_called_once_with(1, 5, 1)


async def test_button_snapshot(
    menuai: menuai,
    mock_homee: MagicMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the multisensor snapshot."""
    mock_homee.nodes = [build_mock_node("buttons.json")]
    mock_homee.get_node_by_id.return_value = mock_homee.nodes[0]
    with patch("menuai.components.homee.PLATFORMS", [Platform.BUTTON]):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)
