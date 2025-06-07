"""Test the Times of the Day integration."""

import pytest

from menuai.components.tod.const import DOMAIN
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry


@pytest.mark.freeze_time("2022-03-16 17:37:00", tz_offset=-7)
async def test_setup_and_remove_config_entry(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test setting up and removing a config entry."""
    tod_entity_id = "binary_sensor.my_tod"

    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            "after_time": "10:00:00",
            "before_time": "18:05:00",
            "name": "My tod",
        },
        title="My tod",
    )
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    # Check the entity is registered in the entity registry
    assert entity_registry.async_get(tod_entity_id) is not None

    # Check the platform is setup correctly
    state = menuai.states.get(tod_entity_id)
    # Check the state of the entity is as expected
    state = menuai.states.get("binary_sensor.my_tod")
    assert state.state == "off"
    assert state.attributes["after"] == "2022-03-16T10:00:00-07:00"
    assert state.attributes["before"] == "2022-03-16T18:05:00-07:00"

    # Remove the config entry
    assert await menuai.config_entries.async_remove(config_entry.entry_id)
    await menuai.async_block_till_done()

    # Check the state and entity registry entry are removed
    assert menuai.states.get(tod_entity_id) is None
    assert entity_registry.async_get(tod_entity_id) is None
