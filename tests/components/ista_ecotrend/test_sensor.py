"""Tests for the ista EcoTrend Sensors."""

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry, snapshot_platform


@pytest.mark.usefixtures("mock_ista", "entity_registry_enabled_by_default")
async def test_setup(
    menuai: menuai,
    ista_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test setup of ista EcoTrend sensor platform."""

    ista_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(ista_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert ista_config_entry.state is ConfigEntryState.LOADED

    await snapshot_platform(menuai, entity_registry, snapshot, ista_config_entry.entry_id)
