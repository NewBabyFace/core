"""Test DROP initialisation."""

from menuai.config_entries import ConfigEntryState
from menuai.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from menuai.core import menuai

from .common import (
    TEST_DATA_HUB,
    TEST_DATA_HUB_RESET,
    TEST_DATA_HUB_TOPIC,
    config_entry_hub,
)

from tests.common import async_fire_mqtt_message
from tests.typing import MqttMockHAClient


async def test_bad_json(menuai: menuai, mqtt_mock: MqttMockHAClient) -> None:
    """Test bad JSON."""
    entry = config_entry_hub()
    entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(entry.entry_id)

    current_flow_sensor_name = "sensor.hub_drop_1_c0ffee_water_flow_rate"
    assert menuai.states.get(current_flow_sensor_name).state == STATE_UNKNOWN

    async_fire_mqtt_message(menuai, TEST_DATA_HUB_TOPIC, "{BAD JSON}")
    await menuai.async_block_till_done()
    assert menuai.states.get(current_flow_sensor_name).state == STATE_UNKNOWN


async def test_unload(menuai: menuai, mqtt_mock: MqttMockHAClient) -> None:
    """Test entity unload."""
    # Load the hub device
    entry = config_entry_hub()
    entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(entry.entry_id)

    current_flow_sensor_name = "sensor.hub_drop_1_c0ffee_water_flow_rate"
    assert menuai.states.get(current_flow_sensor_name).state == STATE_UNKNOWN

    async_fire_mqtt_message(menuai, TEST_DATA_HUB_TOPIC, TEST_DATA_HUB_RESET)
    await menuai.async_block_till_done()
    assert menuai.states.get(current_flow_sensor_name).state == "0.0"

    async_fire_mqtt_message(menuai, TEST_DATA_HUB_TOPIC, TEST_DATA_HUB)
    await menuai.async_block_till_done()

    assert menuai.states.get(current_flow_sensor_name).state == "5.77"

    # Unload the device
    await menuai.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED

    # Verify sensor is unavailable
    assert menuai.states.get(current_flow_sensor_name).state == STATE_UNAVAILABLE


async def test_no_mqtt(menuai: menuai) -> None:
    """Test no MQTT."""
    entry = config_entry_hub()
    entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(entry.entry_id) is False

    protect_mode_select_name = "select.hub_drop_1_c0ffee_protect_mode"
    assert menuai.states.get(protect_mode_select_name) is None
