"""Tests for the Abode binary sensor device."""

from menuai.components.abode import ATTR_DEVICE_ID
from menuai.components.abode.const import ATTRIBUTION
from menuai.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from menuai.const import (
    ATTR_ATTRIBUTION,
    ATTR_DEVICE_CLASS,
    ATTR_FRIENDLY_NAME,
    STATE_OFF,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .common import setup_platform


async def test_entity_registry(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Tests that the devices are registered in the entity registry."""
    await setup_platform(menuai, BINARY_SENSOR_DOMAIN)

    entry = entity_registry.async_get("binary_sensor.front_door")
    assert entry.unique_id == "2834013428b6035fba7d4054aa7b25a3"


async def test_attributes(menuai: menuai) -> None:
    """Test the binary sensor attributes are correct."""
    await setup_platform(menuai, BINARY_SENSOR_DOMAIN)

    state = menuai.states.get("binary_sensor.front_door")
    assert state.state == STATE_OFF
    assert state.attributes.get(ATTR_ATTRIBUTION) == ATTRIBUTION
    assert state.attributes.get(ATTR_DEVICE_ID) == "RF:01430030"
    assert not state.attributes.get("battery_low")
    assert not state.attributes.get("no_response")
    assert state.attributes.get("device_type") == "Door Contact"
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == "Front Door"
    assert state.attributes.get(ATTR_DEVICE_CLASS) == BinarySensorDeviceClass.WINDOW
