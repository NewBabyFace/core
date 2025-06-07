"""Test emoncms sensor."""

from unittest.mock import AsyncMock

from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.emoncms.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration
from .conftest import EMONCMS_FAILURE, get_feed

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform


async def test_no_feed_selected(
    menuai: menuai,
    config_no_feed: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    emoncms_client: AsyncMock,
) -> None:
    """Test with no feed selected."""
    await setup_integration(menuai, config_no_feed)

    assert config_no_feed.state is ConfigEntryState.LOADED
    entity_entries = er.async_entries_for_config_entry(
        entity_registry, config_no_feed.entry_id
    )
    assert entity_entries == []


async def test_no_feed_broadcast(
    menuai: menuai,
    config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    emoncms_client: AsyncMock,
) -> None:
    """Test with no feed broadcasted."""
    emoncms_client.async_request.return_value = {"success": True, "message": []}
    await setup_integration(menuai, config_entry)

    assert config_entry.state is ConfigEntryState.LOADED
    entity_entries = er.async_entries_for_config_entry(
        entity_registry, config_entry.entry_id
    )
    assert entity_entries == []


async def test_coordinator_update(
    menuai: menuai,
    config_single_feed: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    emoncms_client: AsyncMock,
    caplog: pytest.LogCaptureFixture,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test coordinator update."""
    emoncms_client.async_request.return_value = {
        "success": True,
        "message": [get_feed(1, unit="°C")],
    }
    await setup_integration(menuai, config_single_feed)

    await snapshot_platform(
        menuai, entity_registry, snapshot, config_single_feed.entry_id
    )

    async def skip_time() -> None:
        freezer.tick(60)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

    emoncms_client.async_request.return_value = {
        "success": True,
        "message": [get_feed(1, unit="°C", value=24.04, timestamp=1665509670)],
    }

    await skip_time()

    entity_entries = er.async_entries_for_config_entry(
        entity_registry, config_single_feed.entry_id
    )

    for entity_entry in entity_entries:
        state = menuai.states.get(entity_entry.entity_id)
        assert state.attributes["LastUpdated"] == 1665509670
        assert state.state == "24.04"

    emoncms_client.async_request.return_value = EMONCMS_FAILURE

    await skip_time()

    assert f"Error fetching {DOMAIN}_coordinator data" in caplog.text
