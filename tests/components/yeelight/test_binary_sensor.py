"""Test the Yeelight binary sensor."""

from unittest.mock import patch

from menuai.components.yeelight import DOMAIN
from menuai.core import menuai
from menuai.helpers import entity_component
from menuai.setup import async_setup_component

from . import (
    MODULE,
    NAME,
    PROPERTIES,
    YAML_CONFIGURATION,
    _mocked_bulb,
    _patch_discovery,
)

ENTITY_BINARY_SENSOR = f"binary_sensor.{NAME}_nightlight"


async def test_nightlight(menuai: menuai) -> None:
    """Test nightlight sensor."""
    mocked_bulb = _mocked_bulb()
    with _patch_discovery(), patch(f"{MODULE}.AsyncBulb", return_value=mocked_bulb):
        await async_setup_component(menuai, DOMAIN, YAML_CONFIGURATION)
        await menuai.async_block_till_done()

    # active_mode
    assert menuai.states.get(ENTITY_BINARY_SENSOR).state == "off"

    # nl_br
    properties = {**PROPERTIES}
    properties.pop("active_mode")
    mocked_bulb.last_properties = properties
    await entity_component.async_update_entity(menuai, ENTITY_BINARY_SENSOR)
    assert menuai.states.get(ENTITY_BINARY_SENSOR).state == "on"

    # default
    properties.pop("nl_br")
    await entity_component.async_update_entity(menuai, ENTITY_BINARY_SENSOR)
    assert menuai.states.get(ENTITY_BINARY_SENSOR).state == "off"
