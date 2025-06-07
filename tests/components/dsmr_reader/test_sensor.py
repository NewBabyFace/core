"""Tests for DSMR Reader sensor."""

from menuai.components.dsmr_reader.const import DOMAIN
from menuai.components.dsmr_reader.definitions import (
    DSMRReaderSensorEntityDescription,
)
from menuai.components.dsmr_reader.sensor import DSMRSensor
from menuai.const import STATE_UNKNOWN
from menuai.core import menuai

from tests.common import MockConfigEntry, async_fire_mqtt_message
from tests.typing import MqttMockHAClient


async def test_dsmr_sensor_mqtt(
    menuai: menuai,
    mqtt_mock: MqttMockHAClient,
) -> None:
    """Test the DSMRSensor class, via an emluated MQTT message."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title=DOMAIN,
        options={},
        entry_id="TEST_ENTRY_ID",
        unique_id="UNIQUE_TEST_ID",
    )
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    electricity_delivered_1 = "sensor.dsmr_reading_electricity_delivered_1"
    assert menuai.states.get(electricity_delivered_1).state == STATE_UNKNOWN

    electricity_delivered_2 = "sensor.dsmr_reading_electricity_delivered_2"
    assert menuai.states.get(electricity_delivered_2).state == STATE_UNKNOWN

    # Test if the payload is empty
    async_fire_mqtt_message(menuai, "dsmr/reading/electricity_delivered_1", "")
    await menuai.async_block_till_done()
    async_fire_mqtt_message(menuai, "dsmr/reading/electricity_delivered_2", "")
    await menuai.async_block_till_done()

    assert menuai.states.get(electricity_delivered_1).state == STATE_UNKNOWN
    assert menuai.states.get(electricity_delivered_2).state == STATE_UNKNOWN

    # Test if the payload is not empty
    async_fire_mqtt_message(menuai, "dsmr/reading/electricity_delivered_1", "1050.39")
    await menuai.async_block_till_done()
    async_fire_mqtt_message(menuai, "dsmr/reading/electricity_delivered_2", "2001.12")
    await menuai.async_block_till_done()

    assert menuai.states.get(electricity_delivered_1).state == "1050.39"
    assert menuai.states.get(electricity_delivered_2).state == "2001.12"

    # Create a test entity to ensure the entity_description.state is not None
    description = DSMRReaderSensorEntityDescription(
        key="DSMR_TEST_KEY",
        name="DSMR_TEST_NAME",
        state=lambda x: x,
    )
    sensor = DSMRSensor(description, config_entry)
    sensor.menuai = menuai
    await sensor.async_added_to_menuai()
    async_fire_mqtt_message(menuai, "DSMR_TEST_KEY", "192.8")
    await menuai.async_block_till_done()
    assert sensor.native_value == "192.8"
