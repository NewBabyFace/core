"""Tests for the LG Thinq climate platform."""

from unittest.mock import AsyncMock, patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.util.unit_system import US_CUSTOMARY_SYSTEM

from . import setup_integration

from tests.common import MockConfigEntry, snapshot_platform


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_all_entities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_thinq_api: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    menuai.config.units = US_CUSTOMARY_SYSTEM
    with patch("menuai.components.lg_thinq.PLATFORMS", [Platform.CLIMATE]):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)
