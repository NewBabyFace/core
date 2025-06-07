"""The tests for the Canary sensor platform."""

from datetime import timedelta
from unittest.mock import patch

from menuai.components.canary.const import DOMAIN, MANUFACTURER
from menuai.components.canary.sensor import (
    ATTR_AIR_QUALITY,
    STATE_AIR_QUALITY_ABNORMAL,
    STATE_AIR_QUALITY_NORMAL,
    STATE_AIR_QUALITY_VERY_ABNORMAL,
)
from menuai.components.sensor import SensorDeviceClass
from menuai.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfTemperature,
)
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.helpers.entity_component import async_update_entity
from menuai.util.dt import utcnow

from . import init_integration, mock_device, mock_location, mock_reading

from tests.common import async_fire_time_changed


async def test_sensors_pro(
    menuai: menuai,
    canary,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test the creation and values of the sensors for Canary Pro."""
    online_device_at_home = mock_device(20, "Dining Room", True, "Canary Pro")

    instance = canary.return_value
    instance.get_locations.return_value = [
        mock_location(100, "Home", True, devices=[online_device_at_home]),
    ]

    instance.get_latest_readings.return_value = [
        mock_reading("temperature", "21.12"),
        mock_reading("humidity", "50.46"),
        mock_reading("air_quality", "0.59"),
    ]

    with patch("menuai.components.canary.PLATFORMS", ["sensor"]):
        await init_integration(menuai)

    sensors = {
        "home_dining_room_temperature": (
            "20_temperature",
            "21.12",
            UnitOfTemperature.CELSIUS,
            SensorDeviceClass.TEMPERATURE,
            None,
        ),
        "home_dining_room_humidity": (
            "20_humidity",
            "50.46",
            PERCENTAGE,
            SensorDeviceClass.HUMIDITY,
            None,
        ),
        "home_dining_room_air_quality": (
            "20_air_quality",
            "0.59",
            None,
            None,
            "mdi:weather-windy",
        ),
    }

    for sensor_id, data in sensors.items():
        entity_entry = entity_registry.async_get(f"sensor.{sensor_id}")
        assert entity_entry
        assert entity_entry.original_device_class == data[3]
        assert entity_entry.unique_id == data[0]
        assert entity_entry.original_icon == data[4]

        state = menuai.states.get(f"sensor.{sensor_id}")
        assert state
        assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == data[2]
        assert state.state == data[1]

    device = device_registry.async_get_device(identifiers={(DOMAIN, "20")})
    assert device
    assert device.manufacturer == MANUFACTURER
    assert device.name == "Dining Room"
    assert device.model == "Canary Pro"


async def test_sensors_attributes_pro(menuai: menuai, canary) -> None:
    """Test the creation and values of the sensors attributes for Canary Pro."""

    online_device_at_home = mock_device(20, "Dining Room", True, "Canary Pro")

    instance = canary.return_value
    instance.get_locations.return_value = [
        mock_location(100, "Home", True, devices=[online_device_at_home]),
    ]

    instance.get_latest_readings.return_value = [
        mock_reading("temperature", "21.12"),
        mock_reading("humidity", "50.46"),
        mock_reading("air_quality", "0.59"),
    ]

    with patch("menuai.components.canary.PLATFORMS", ["sensor"]):
        await init_integration(menuai)

    entity_id = "sensor.home_dining_room_air_quality"
    state1 = menuai.states.get(entity_id)
    assert state1
    assert state1.state == "0.59"
    assert state1.attributes[ATTR_AIR_QUALITY] == STATE_AIR_QUALITY_ABNORMAL

    instance.get_latest_readings.return_value = [
        mock_reading("temperature", "21.12"),
        mock_reading("humidity", "50.46"),
        mock_reading("air_quality", "0.4"),
    ]

    future = utcnow() + timedelta(seconds=30)
    async_fire_time_changed(menuai, future)
    await async_update_entity(menuai, entity_id)
    await menuai.async_block_till_done()

    state2 = menuai.states.get(entity_id)
    assert state2
    assert state2.state == "0.4"
    assert state2.attributes[ATTR_AIR_QUALITY] == STATE_AIR_QUALITY_VERY_ABNORMAL

    instance.get_latest_readings.return_value = [
        mock_reading("temperature", "21.12"),
        mock_reading("humidity", "50.46"),
        mock_reading("air_quality", "1.0"),
    ]

    future += timedelta(seconds=30)
    async_fire_time_changed(menuai, future)
    await async_update_entity(menuai, entity_id)
    await menuai.async_block_till_done()

    state3 = menuai.states.get(entity_id)
    assert state3
    assert state3.state == "1.0"
    assert state3.attributes[ATTR_AIR_QUALITY] == STATE_AIR_QUALITY_NORMAL


async def test_sensors_flex(
    menuai: menuai,
    canary,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test the creation and values of the sensors for Canary Flex."""
    online_device_at_home = mock_device(20, "Dining Room", True, "Canary Flex")

    instance = canary.return_value
    instance.get_locations.return_value = [
        mock_location(100, "Home", True, devices=[online_device_at_home]),
    ]

    instance.get_latest_readings.return_value = [
        mock_reading("battery", "70.4567"),
        mock_reading("wifi", "-57"),
    ]

    with patch("menuai.components.canary.PLATFORMS", ["sensor"]):
        await init_integration(menuai)

    sensors = {
        "home_dining_room_battery": (
            "20_battery",
            "70.46",
            PERCENTAGE,
            SensorDeviceClass.BATTERY,
            None,
        ),
        "home_dining_room_wifi": (
            "20_wifi",
            "-57.0",
            SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
            SensorDeviceClass.SIGNAL_STRENGTH,
            None,
        ),
    }

    for sensor_id, data in sensors.items():
        entity_entry = entity_registry.async_get(f"sensor.{sensor_id}")
        assert entity_entry
        assert entity_entry.original_device_class == data[3]
        assert entity_entry.unique_id == data[0]
        assert entity_entry.original_icon == data[4]

        state = menuai.states.get(f"sensor.{sensor_id}")
        assert state
        assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == data[2]
        assert state.state == data[1]

    device = device_registry.async_get_device(identifiers={(DOMAIN, "20")})
    assert device
    assert device.manufacturer == MANUFACTURER
    assert device.name == "Dining Room"
    assert device.model == "Canary Flex"
