"""Tests for the Lektrico switch platform."""

from unittest.mock import AsyncMock, patch

from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, snapshot_platform


async def test_all_entities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_device: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""

    with patch.multiple(
        "menuai.components.lektrico",
        CHARGERS_PLATFORMS=[Platform.SWITCH],
        LB_DEVICES_PLATFORMS=[Platform.SWITCH],
    ):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)
