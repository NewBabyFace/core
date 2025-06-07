"""Test DROP switch entities."""

from menuai.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from menuai.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON, STATE_UNKNOWN
from menuai.core import menuai

from .common import (
    TEST_DATA_FILTER,
    TEST_DATA_FILTER_RESET,
    TEST_DATA_FILTER_TOPIC,
    TEST_DATA_HUB,
    TEST_DATA_HUB_RESET,
    TEST_DATA_HUB_TOPIC,
    TEST_DATA_PROTECTION_VALVE,
    TEST_DATA_PROTECTION_VALVE_RESET,
    TEST_DATA_PROTECTION_VALVE_TOPIC,
    TEST_DATA_SOFTENER,
    TEST_DATA_SOFTENER_RESET,
    TEST_DATA_SOFTENER_TOPIC,
    config_entry_filter,
    config_entry_hub,
    config_entry_protection_valve,
    config_entry_softener,
)

from tests.common import async_fire_mqtt_message
from tests.typing import MqttMockHAClient


async def test_switches_hub(menuai: menuai, mqtt_mock: MqttMockHAClient) -> None:
    """Test DROP switches for hubs."""
    entry = config_entry_hub()
    entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(entry.entry_id)

    water_supply_switch_name = "switch.hub_drop_1_c0ffee_water_supply"
    assert menuai.states.get(water_supply_switch_name).state == STATE_UNKNOWN
    bypass_switch_name = "switch.hub_drop_1_c0ffee_treatment_bypass"
    assert menuai.states.get(bypass_switch_name).state == STATE_UNKNOWN

    async_fire_mqtt_message(menuai, TEST_DATA_HUB_TOPIC, TEST_DATA_HUB_RESET)
    await menuai.async_block_till_done()
    assert menuai.states.get(water_supply_switch_name).state == STATE_OFF
    assert menuai.states.get(bypass_switch_name).state == STATE_ON

    async_fire_mqtt_message(menuai, TEST_DATA_HUB_TOPIC, TEST_DATA_HUB)
    await menuai.async_block_till_done()
    assert menuai.states.get(water_supply_switch_name).state == STATE_ON
    assert menuai.states.get(bypass_switch_name).state == STATE_OFF

    # Test switch turn off method.
    mqtt_mock.async_publish.reset_mock()
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: water_supply_switch_name},
        blocking=True,
    )
    assert len(mqtt_mock.async_publish.mock_calls) == 1

    # Simulate response from the hub
    async_fire_mqtt_message(menuai, TEST_DATA_HUB_TOPIC, TEST_DATA_HUB_RESET)
    await menuai.async_block_till_done()
    assert menuai.states.get(water_supply_switch_name).state == STATE_OFF

    # Test switch turn on method.
    mqtt_mock.async_publish.reset_mock()
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: water_supply_switch_name},
        blocking=True,
    )
    assert len(mqtt_mock.async_publish.mock_calls) == 1

    # Simulate response from the hub
    async_fire_mqtt_message(menuai, TEST_DATA_HUB_TOPIC, TEST_DATA_HUB)
    await menuai.async_block_till_done()
    assert menuai.states.get(water_supply_switch_name).state == STATE_ON

    # Test switch turn on method.
    mqtt_mock.async_publish.reset_mock()
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: bypass_switch_name},
        blocking=True,
    )
    assert len(mqtt_mock.async_publish.mock_calls) == 1

    # Simulate response from the device
    async_fire_mqtt_message(menuai, TEST_DATA_HUB_TOPIC, TEST_DATA_HUB_RESET)
    await menuai.async_block_till_done()
    assert menuai.states.get(bypass_switch_name).state == STATE_ON

    # Test switch turn off method.
    mqtt_mock.async_publish.reset_mock()
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: bypass_switch_name},
        blocking=True,
    )
    assert len(mqtt_mock.async_publish.mock_calls) == 1

    # Simulate response from the device
    async_fire_mqtt_message(menuai, TEST_DATA_HUB_TOPIC, TEST_DATA_HUB)
    await menuai.async_block_till_done()
    assert menuai.states.get(bypass_switch_name).state == STATE_OFF


async def test_switches_protection_valve(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test DROP switches for protection valves."""
    entry = config_entry_protection_valve()
    entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(entry.entry_id)

    water_supply_switch_name = "switch.protection_valve_water_supply"
    assert menuai.states.get(water_supply_switch_name).state == STATE_UNKNOWN

    async_fire_mqtt_message(
        menuai, TEST_DATA_PROTECTION_VALVE_TOPIC, TEST_DATA_PROTECTION_VALVE_RESET
    )
    await menuai.async_block_till_done()
    assert menuai.states.get(water_supply_switch_name).state == STATE_OFF

    async_fire_mqtt_message(
        menuai, TEST_DATA_PROTECTION_VALVE_TOPIC, TEST_DATA_PROTECTION_VALVE
    )
    await menuai.async_block_till_done()
    assert menuai.states.get(water_supply_switch_name).state == STATE_ON

    # Test switch turn off method.
    mqtt_mock.async_publish.reset_mock()
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: water_supply_switch_name},
        blocking=True,
    )
    assert len(mqtt_mock.async_publish.mock_calls) == 1

    # Simulate response from the device
    async_fire_mqtt_message(
        menuai, TEST_DATA_PROTECTION_VALVE_TOPIC, TEST_DATA_PROTECTION_VALVE_RESET
    )
    await menuai.async_block_till_done()
    assert menuai.states.get(water_supply_switch_name).state == STATE_OFF

    # Test switch turn on method.
    mqtt_mock.async_publish.reset_mock()
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: water_supply_switch_name},
        blocking=True,
    )
    assert len(mqtt_mock.async_publish.mock_calls) == 1

    # Simulate response from the device
    async_fire_mqtt_message(
        menuai, TEST_DATA_PROTECTION_VALVE_TOPIC, TEST_DATA_PROTECTION_VALVE
    )
    await menuai.async_block_till_done()
    assert menuai.states.get(water_supply_switch_name).state == STATE_ON


async def test_switches_softener(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test DROP switches for softeners."""
    entry = config_entry_softener()
    entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(entry.entry_id)

    bypass_switch_name = "switch.softener_treatment_bypass"
    assert menuai.states.get(bypass_switch_name).state == STATE_UNKNOWN

    async_fire_mqtt_message(menuai, TEST_DATA_SOFTENER_TOPIC, TEST_DATA_SOFTENER_RESET)
    await menuai.async_block_till_done()
    assert menuai.states.get(bypass_switch_name).state == STATE_ON

    async_fire_mqtt_message(menuai, TEST_DATA_SOFTENER_TOPIC, TEST_DATA_SOFTENER)
    await menuai.async_block_till_done()
    assert menuai.states.get(bypass_switch_name).state == STATE_OFF

    # Test switch turn on method.
    mqtt_mock.async_publish.reset_mock()
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: bypass_switch_name},
        blocking=True,
    )
    assert len(mqtt_mock.async_publish.mock_calls) == 1

    # Simulate response from the device
    async_fire_mqtt_message(menuai, TEST_DATA_SOFTENER_TOPIC, TEST_DATA_SOFTENER_RESET)
    await menuai.async_block_till_done()
    assert menuai.states.get(bypass_switch_name).state == STATE_ON

    # Test switch turn off method.
    mqtt_mock.async_publish.reset_mock()
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: bypass_switch_name},
        blocking=True,
    )
    assert len(mqtt_mock.async_publish.mock_calls) == 1

    # Simulate response from the device
    async_fire_mqtt_message(menuai, TEST_DATA_SOFTENER_TOPIC, TEST_DATA_SOFTENER)
    await menuai.async_block_till_done()
    assert menuai.states.get(bypass_switch_name).state == STATE_OFF


async def test_switches_filter(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test DROP switches for filters."""
    entry = config_entry_filter()
    entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(entry.entry_id)

    bypass_switch_name = "switch.filter_treatment_bypass"
    assert menuai.states.get(bypass_switch_name).state == STATE_UNKNOWN

    async_fire_mqtt_message(menuai, TEST_DATA_FILTER_TOPIC, TEST_DATA_FILTER_RESET)
    await menuai.async_block_till_done()
    assert menuai.states.get(bypass_switch_name).state == STATE_ON

    async_fire_mqtt_message(menuai, TEST_DATA_FILTER_TOPIC, TEST_DATA_FILTER)
    await menuai.async_block_till_done()
    assert menuai.states.get(bypass_switch_name).state == STATE_OFF

    # Test switch turn on method.
    mqtt_mock.async_publish.reset_mock()
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: bypass_switch_name},
        blocking=True,
    )
    assert len(mqtt_mock.async_publish.mock_calls) == 1

    # Simulate response from the device
    async_fire_mqtt_message(menuai, TEST_DATA_FILTER_TOPIC, TEST_DATA_FILTER_RESET)
    await menuai.async_block_till_done()
    assert menuai.states.get(bypass_switch_name).state == STATE_ON

    # Test switch turn off method.
    mqtt_mock.async_publish.reset_mock()
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: bypass_switch_name},
        blocking=True,
    )
    assert len(mqtt_mock.async_publish.mock_calls) == 1

    # Simulate response from the device
    async_fire_mqtt_message(menuai, TEST_DATA_FILTER_TOPIC, TEST_DATA_FILTER)
    await menuai.async_block_till_done()
    assert menuai.states.get(bypass_switch_name).state == STATE_OFF
