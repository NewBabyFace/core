"""Tests for the Lutron Caseta integration."""

from menuai.const import STATE_ON
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import MockBridge, async_setup_integration


async def test_light_unique_id(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test a light unique id."""
    await async_setup_integration(menuai, MockBridge)

    ra3_entity_id = "light.basement_bedroom_main_lights"
    caseta_entity_id = "light.kitchen_main_lights"

    # Assert that RA3 lights will have the bridge serial hash and the zone id as the uniqueID
    assert entity_registry.async_get(ra3_entity_id).unique_id == "000004d2_801"

    # Assert that Caseta lights will have the serial number as the uniqueID
    assert entity_registry.async_get(caseta_entity_id).unique_id == "5442321"

    state = menuai.states.get(ra3_entity_id)
    assert state.state == STATE_ON
