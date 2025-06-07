"""Tests for the Geniushub switch platform."""

from unittest.mock import patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, snapshot_platform


@pytest.mark.usefixtures("mock_geniushub_cloud")
async def test_cloud_all_sensors(
    menuai: menuai,
    mock_cloud_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the creation of the Genius Hub switch entities."""
    with patch("menuai.components.geniushub.PLATFORMS", [Platform.SWITCH]):
        await setup_integration(menuai, mock_cloud_config_entry)

    await snapshot_platform(
        menuai, entity_registry, snapshot, mock_cloud_config_entry.entry_id
    )
