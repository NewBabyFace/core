"""Test the Tessie media player platform."""

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from syrupy.assertion import SnapshotAssertion

from menuai.components.tessie.coordinator import TESSIE_SYNC_INTERVAL
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .common import setup_platform

from tests.common import async_fire_time_changed

WAIT = timedelta(seconds=TESSIE_SYNC_INTERVAL)


async def test_media_player(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    mock_get_state,
    mock_get_status,
) -> None:
    """Tests that the media player entity is correct when idle."""

    entry = await setup_platform(menuai, [Platform.MEDIA_PLAYER])

    entity_entries = er.async_entries_for_config_entry(entity_registry, entry.entry_id)

    assert entity_entries
    for entity_entry in entity_entries:
        assert entity_entry == snapshot(name=f"{entity_entry.entity_id}-entry")
        assert (state := menuai.states.get(entity_entry.entity_id))
        assert state == snapshot(name=f"{entity_entry.entity_id}-paused")

        # The refresh fixture has music playing
        freezer.tick(WAIT)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)

        assert menuai.states.get(entity_entry.entity_id) == snapshot(
            name=f"{entity_entry.entity_id}-playing"
        )
