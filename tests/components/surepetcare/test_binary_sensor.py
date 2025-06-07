"""The tests for the Sure Petcare binary sensor platform."""

from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import HOUSEHOLD_ID, HUB_ID

from tests.common import MockConfigEntry

EXPECTED_ENTITY_IDS = {
    "binary_sensor.pet_flap_connectivity": f"{HOUSEHOLD_ID}-13576-connectivity",
    "binary_sensor.cat_flap_connectivity": f"{HOUSEHOLD_ID}-13579-connectivity",
    "binary_sensor.feeder_connectivity": f"{HOUSEHOLD_ID}-12345-connectivity",
    "binary_sensor.pet": f"{HOUSEHOLD_ID}-24680",
    "binary_sensor.hub": f"{HOUSEHOLD_ID}-{HUB_ID}",
}


async def test_binary_sensors(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    surepetcare,
    mock_config_entry_setup: MockConfigEntry,
) -> None:
    """Test the generation of unique ids."""
    state_entity_ids = menuai.states.async_entity_ids()

    for entity_id, unique_id in EXPECTED_ENTITY_IDS.items():
        assert entity_id in state_entity_ids
        state = menuai.states.get(entity_id)
        assert state
        assert state.state == "on"
        entity = entity_registry.async_get(entity_id)
        assert entity.unique_id == unique_id
