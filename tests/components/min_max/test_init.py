"""Test the Min/Max integration."""

import pytest

from menuai.components.min_max.const import DOMAIN
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry


@pytest.mark.parametrize("platform", ["sensor"])
async def test_setup_and_remove_config_entry(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    platform: str,
) -> None:
    """Test setting up and removing a config entry."""
    menuai.states.async_set("sensor.input_one", "10")
    menuai.states.async_set("sensor.input_two", "20")

    input_sensors = ["sensor.input_one", "sensor.input_two"]

    min_max_entity_id = f"{platform}.my_min_max"

    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            "entity_ids": input_sensors,
            "name": "My min_max",
            "round_digits": 2.0,
            "type": "max",
        },
        title="My min_max",
    )
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    # Check the entity is registered in the entity registry
    assert entity_registry.async_get(min_max_entity_id) is not None

    # Check the platform is setup correctly
    state = menuai.states.get(min_max_entity_id)
    assert state.state == "20.0"

    # Remove the config entry
    assert await menuai.config_entries.async_remove(config_entry.entry_id)
    await menuai.async_block_till_done()

    # Check the state and entity registry entry are removed
    assert menuai.states.get(min_max_entity_id) is None
    assert entity_registry.async_get(min_max_entity_id) is None
