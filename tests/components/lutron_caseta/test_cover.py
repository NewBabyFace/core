"""Tests for the Lutron Caseta integration."""

from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import MockBridge, async_setup_integration


async def test_cover_unique_id(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test a light unique id."""
    await async_setup_integration(menuai, MockBridge)

    cover_entity_id = "cover.basement_bedroom_left_shade"

    # Assert that Caseta covers will have the bridge serial hash and the zone id as the uniqueID
    assert entity_registry.async_get(cover_entity_id).unique_id == "000004d2_802"
