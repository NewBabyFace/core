"""Test DROP binary sensor entities."""

from unittest.mock import patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.const import STATE_OFF, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .common import (
    TEST_DATA_ALERT,
    TEST_DATA_ALERT_RESET,
    TEST_DATA_ALERT_TOPIC,
    TEST_DATA_HUB,
    TEST_DATA_HUB_RESET,
    TEST_DATA_HUB_TOPIC,
    TEST_DATA_LEAK,
    TEST_DATA_LEAK_RESET,
    TEST_DATA_LEAK_TOPIC,
    TEST_DATA_PROTECTION_VALVE,
    TEST_DATA_PROTECTION_VALVE_RESET,
    TEST_DATA_PROTECTION_VALVE_TOPIC,
    TEST_DATA_PUMP_CONTROLLER,
    TEST_DATA_PUMP_CONTROLLER_RESET,
    TEST_DATA_PUMP_CONTROLLER_TOPIC,
    TEST_DATA_RO_FILTER,
    TEST_DATA_RO_FILTER_RESET,
    TEST_DATA_RO_FILTER_TOPIC,
    TEST_DATA_SOFTENER,
    TEST_DATA_SOFTENER_RESET,
    TEST_DATA_SOFTENER_TOPIC,
    config_entry_alert,
    config_entry_hub,
    config_entry_leak,
    config_entry_protection_valve,
    config_entry_pump_controller,
    config_entry_ro_filter,
    config_entry_softener,
)

from tests.common import MockConfigEntry, async_fire_mqtt_message
from tests.typing import MqttMockHAClient


@pytest.mark.parametrize(
    ("config_entry", "topic", "reset", "data"),
    [
        (config_entry_hub(), TEST_DATA_HUB_TOPIC, TEST_DATA_HUB_RESET, TEST_DATA_HUB),
        (
            config_entry_alert(),
            TEST_DATA_ALERT_TOPIC,
            TEST_DATA_ALERT_RESET,
            TEST_DATA_ALERT,
        ),
        (
            config_entry_leak(),
            TEST_DATA_LEAK_TOPIC,
            TEST_DATA_LEAK_RESET,
            TEST_DATA_LEAK,
        ),
        (
            config_entry_softener(),
            TEST_DATA_SOFTENER_TOPIC,
            TEST_DATA_SOFTENER_RESET,
            TEST_DATA_SOFTENER,
        ),
        (
            config_entry_protection_valve(),
            TEST_DATA_PROTECTION_VALVE_TOPIC,
            TEST_DATA_PROTECTION_VALVE_RESET,
            TEST_DATA_PROTECTION_VALVE,
        ),
        (
            config_entry_pump_controller(),
            TEST_DATA_PUMP_CONTROLLER_TOPIC,
            TEST_DATA_PUMP_CONTROLLER_RESET,
            TEST_DATA_PUMP_CONTROLLER,
        ),
        (
            config_entry_ro_filter(),
            TEST_DATA_RO_FILTER_TOPIC,
            TEST_DATA_RO_FILTER_RESET,
            TEST_DATA_RO_FILTER,
        ),
    ],
    ids=[
        "hub",
        "alert",
        "leak",
        "softener",
        "protection_valve",
        "pump_controller",
        "ro_filter",
    ],
)
async def test_sensors(
    menuai: menuai,
    mqtt_mock: MqttMockHAClient,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    config_entry: MockConfigEntry,
    topic: str,
    reset: str,
    data: str,
) -> None:
    """Test DROP sensors."""
    config_entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.drop_connect.PLATFORMS", [Platform.BINARY_SENSOR]
    ):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    entity_entries = er.async_entries_for_config_entry(
        entity_registry, config_entry.entry_id
    )

    assert entity_entries
    for entity_entry in entity_entries:
        assert menuai.states.get(entity_entry.entity_id).state == STATE_OFF

    async_fire_mqtt_message(menuai, topic, reset)
    await menuai.async_block_till_done()

    entity_entries = er.async_entries_for_config_entry(
        entity_registry, config_entry.entry_id
    )

    assert entity_entries
    for entity_entry in entity_entries:
        assert menuai.states.get(entity_entry.entity_id).state == STATE_OFF

    async_fire_mqtt_message(menuai, topic, data)
    await menuai.async_block_till_done()

    entity_entries = er.async_entries_for_config_entry(
        entity_registry, config_entry.entry_id
    )
    assert entity_entries
    for entity_entry in entity_entries:
        assert entity_entry == snapshot(name=f"{entity_entry.entity_id}-entry")
        assert menuai.states.get(entity_entry.entity_id) == snapshot(
            name=f"{entity_entry.entity_id}-state"
        )
