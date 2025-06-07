"""Test the RAPT Pill BLE sensors."""

from __future__ import annotations

from menuai.components.rapt_ble.const import DOMAIN
from menuai.components.sensor import ATTR_STATE_CLASS, SensorStateClass
from menuai.const import (
    ATTR_FRIENDLY_NAME,
    ATTR_UNIT_OF_MEASUREMENT,
    PERCENTAGE,
    UnitOfTemperature,
)
from menuai.core import menuai

from . import COMPLETE_SERVICE_INFO, RAPT_MAC

from tests.common import MockConfigEntry
from tests.components.bluetooth import inject_bluetooth_service_info


async def test_sensors(menuai: menuai) -> None:
    """Test setting up creates the sensors."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=RAPT_MAC,
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 0
    inject_bluetooth_service_info(menuai, COMPLETE_SERVICE_INFO)
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) == 3

    temp_sensor = menuai.states.get("sensor.rapt_pill_0666_battery")
    assert temp_sensor is not None

    temp_sensor_attributes = temp_sensor.attributes
    assert temp_sensor.state == "43"
    assert temp_sensor_attributes[ATTR_FRIENDLY_NAME] == "RAPT Pill 0666 Battery"
    assert temp_sensor_attributes[ATTR_UNIT_OF_MEASUREMENT] == PERCENTAGE
    assert temp_sensor_attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT

    temp_sensor = menuai.states.get("sensor.rapt_pill_0666_temperature")
    assert temp_sensor is not None

    temp_sensor_attributes = temp_sensor.attributes
    assert temp_sensor.state == "23.81"
    assert temp_sensor_attributes[ATTR_FRIENDLY_NAME] == "RAPT Pill 0666 Temperature"
    assert temp_sensor_attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert temp_sensor_attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT

    temp_sensor = menuai.states.get("sensor.rapt_pill_0666_specific_gravity")
    assert temp_sensor is not None

    temp_sensor_attributes = temp_sensor.attributes
    assert temp_sensor.state == "1.0111"
    assert (
        temp_sensor_attributes[ATTR_FRIENDLY_NAME] == "RAPT Pill 0666 Specific Gravity"
    )
    assert temp_sensor_attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()
