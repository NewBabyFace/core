"""Tests for the Smarty switch platform."""

from unittest.mock import AsyncMock, patch

from syrupy.assertion import SnapshotAssertion

from menuai.components.switch import DOMAIN as SWITCH_DOMAIN
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    Platform,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, snapshot_platform


async def test_all_entities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_smarty: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    with patch("menuai.components.smarty.PLATFORMS", [Platform.SWITCH]):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_setting_value(
    menuai: menuai,
    mock_smarty: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setting value."""
    await setup_integration(menuai, mock_config_entry)

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        target={ATTR_ENTITY_ID: "switch.mock_title_boost"},
        blocking=True,
    )
    mock_smarty.enable_boost.assert_called_once_with()

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        target={ATTR_ENTITY_ID: "switch.mock_title_boost"},
        blocking=True,
    )
    mock_smarty.disable_boost.assert_called_once_with()
