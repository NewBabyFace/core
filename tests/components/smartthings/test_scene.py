"""Test for the SmartThings scene platform."""

from unittest.mock import AsyncMock

from syrupy.assertion import SnapshotAssertion

from menuai.components.scene import DOMAIN as SCENE_DOMAIN
from menuai.const import ATTR_ENTITY_ID, SERVICE_TURN_ON, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration, snapshot_smartthings_entities

from tests.common import MockConfigEntry


async def test_all_entities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_smartthings: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    await setup_integration(menuai, mock_config_entry)

    snapshot_smartthings_entities(menuai, entity_registry, snapshot, Platform.SCENE)


async def test_activate_scene(
    menuai: menuai,
    mock_smartthings: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test activating a scene."""
    await setup_integration(menuai, mock_config_entry)

    await menuai.services.async_call(
        SCENE_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "scene.away"},
        blocking=True,
    )

    mock_smartthings.execute_scene.assert_called_once_with(
        "743b0f37-89b8-476c-aedf-eea8ad8cd29d"
    )
