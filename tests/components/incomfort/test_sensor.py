"""Sensor tests for Intergas InComfort integration."""

from unittest.mock import MagicMock, patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from tests.common import snapshot_platform


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
@patch("menuai.components.incomfort.PLATFORMS", [Platform.SENSOR])
async def test_setup_platform(
    menuai: menuai,
    mock_incomfort: MagicMock,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test the incomfort entities are set up correctly."""
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)
