"""Test the Tessie device tracker platform."""

from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .common import assert_entities, setup_platform


async def test_device_tracker(
    menuai: menuai, snapshot: SnapshotAssertion, entity_registry: er.EntityRegistry
) -> None:
    """Tests that the device tracker entities are correct."""

    entry = await setup_platform(menuai, [Platform.DEVICE_TRACKER])

    assert_entities(menuai, entry.entry_id, entity_registry, snapshot)
