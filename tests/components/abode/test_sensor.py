"""Tests for the Abode sensor device."""

import pytest

from menuai.components.abode import ATTR_DEVICE_ID
from menuai.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from menuai.const import (
    ATTR_DEVICE_CLASS,
    ATTR_FRIENDLY_NAME,
    ATTR_UNIT_OF_MEASUREMENT,
    PERCENTAGE,
    UnitOfTemperature,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .common import setup_platform


async def test_entity_registry(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Tests that the devices are registered in the entity registry."""
    await setup_platform(menuai, SENSOR_DOMAIN)

    entry = entity_registry.async_get("sensor.environment_sensor_humidity")
    assert entry.unique_id == "13545b21f4bdcd33d9abd461f8443e65-humidity"


async def test_attributes(menuai: menuai) -> None:
    """Test the sensor attributes are correct."""
    await setup_platform(menuai, SENSOR_DOMAIN)

    state = menuai.states.get("sensor.environment_sensor_humidity")
    assert state.state == "32.0"
    assert state.attributes.get(ATTR_DEVICE_ID) == "RF:02148e70"
    assert not state.attributes.get("battery_low")
    assert not state.attributes.get("no_response")
    assert state.attributes.get("device_type") == "LM"
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == PERCENTAGE
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == "Environment Sensor Humidity"
    assert state.attributes.get(ATTR_DEVICE_CLASS) == SensorDeviceClass.HUMIDITY

    state = menuai.states.get("sensor.environment_sensor_illuminance")
    assert state.state == "1.0"
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "lx"

    state = menuai.states.get("sensor.environment_sensor_temperature")
    # Abodepy device JSON reports 19.5, but MenuAI shows 19.4
    assert float(state.state) == pytest.approx(19.44444)
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfTemperature.CELSIUS
