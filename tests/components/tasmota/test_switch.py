"""The tests for the Tasmota switch platform."""

import copy
import json
from unittest.mock import patch

from hatasmota.utils import (
    get_topic_stat_result,
    get_topic_tele_state,
    get_topic_tele_will,
)
import pytest

from menuai.components.tasmota.const import DEFAULT_PREFIX
from menuai.const import ATTR_ASSUMED_STATE, STATE_OFF, STATE_ON, Platform
from menuai.core import menuai

from .test_common import (
    DEFAULT_CONFIG,
    help_test_availability,
    help_test_availability_discovery_update,
    help_test_availability_poll_state,
    help_test_availability_when_connection_lost,
    help_test_deep_sleep_availability,
    help_test_deep_sleep_availability_when_connection_lost,
    help_test_discovery_device_remove,
    help_test_discovery_removal,
    help_test_discovery_update_unchanged,
    help_test_entity_id_update_discovery_update,
    help_test_entity_id_update_subscriptions,
)

from tests.common import async_fire_mqtt_message
from tests.components.switch import common
from tests.typing import MqttMockHAClient, MqttMockPahoClient


async def test_controlling_state_via_mqtt(
    menuai: menuai, mqtt_mock: MqttMockHAClient, setup_tasmota
) -> None:
    """Test state update via MQTT."""
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["rl"][0] = 1
    mac = config["mac"]

    async_fire_mqtt_message(
        menuai,
        f"{DEFAULT_PREFIX}/{mac}/config",
        json.dumps(config),
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("switch.tasmota_test")
    assert state.state == "unavailable"
    assert not state.attributes.get(ATTR_ASSUMED_STATE)

    async_fire_mqtt_message(menuai, "tasmota_49A3BC/tele/LWT", "Online")
    await menuai.async_block_till_done()
    state = menuai.states.get("switch.tasmota_test")
    assert state.state == STATE_OFF
    assert not state.attributes.get(ATTR_ASSUMED_STATE)

    async_fire_mqtt_message(menuai, "tasmota_49A3BC/tele/STATE", '{"POWER":"ON"}')

    state = menuai.states.get("switch.tasmota_test")
    assert state.state == STATE_ON

    async_fire_mqtt_message(menuai, "tasmota_49A3BC/tele/STATE", '{"POWER":"OFF"}')

    state = menuai.states.get("switch.tasmota_test")
    assert state.state == STATE_OFF

    async_fire_mqtt_message(menuai, "tasmota_49A3BC/stat/RESULT", '{"POWER":"ON"}')

    state = menuai.states.get("switch.tasmota_test")
    assert state.state == STATE_ON

    async_fire_mqtt_message(menuai, "tasmota_49A3BC/stat/RESULT", '{"POWER":"OFF"}')

    state = menuai.states.get("switch.tasmota_test")
    assert state.state == STATE_OFF


async def test_sending_mqtt_commands(
    menuai: menuai, mqtt_mock: MqttMockHAClient, setup_tasmota
) -> None:
    """Test the sending MQTT commands."""
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["rl"][0] = 1
    mac = config["mac"]

    async_fire_mqtt_message(
        menuai,
        f"{DEFAULT_PREFIX}/{mac}/config",
        json.dumps(config),
    )
    await menuai.async_block_till_done()

    async_fire_mqtt_message(menuai, "tasmota_49A3BC/tele/LWT", "Online")
    await menuai.async_block_till_done()
    state = menuai.states.get("switch.tasmota_test")
    assert state.state == STATE_OFF
    await menuai.async_block_till_done()
    await menuai.async_block_till_done()
    mqtt_mock.async_publish.reset_mock()

    # Turn the switch on and verify MQTT message is sent
    await common.async_turn_on(menuai, "switch.tasmota_test")
    mqtt_mock.async_publish.assert_called_once_with(
        "tasmota_49A3BC/cmnd/Power1", "ON", 0, False
    )
    mqtt_mock.async_publish.reset_mock()

    # Tasmota is not optimistic, the state should still be off
    state = menuai.states.get("switch.tasmota_test")
    assert state.state == STATE_OFF

    # Turn the switch off and verify MQTT message is sent
    await common.async_turn_off(menuai, "switch.tasmota_test")
    mqtt_mock.async_publish.assert_called_once_with(
        "tasmota_49A3BC/cmnd/Power1", "OFF", 0, False
    )

    state = menuai.states.get("switch.tasmota_test")
    assert state.state == STATE_OFF


async def test_relay_as_light(
    menuai: menuai, mqtt_mock: MqttMockHAClient, setup_tasmota
) -> None:
    """Test relay does not show up as switch in light mode."""
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["rl"][0] = 1
    config["so"]["30"] = 1  # Enforce MenuAI auto-discovery as light
    mac = config["mac"]

    async_fire_mqtt_message(
        menuai,
        f"{DEFAULT_PREFIX}/{mac}/config",
        json.dumps(config),
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("switch.tasmota_test")
    assert state is None
    state = menuai.states.get("light.tasmota_test")
    assert state is not None


async def test_availability_when_connection_lost(
    menuai: menuai,
    mqtt_client_mock: MqttMockPahoClient,
    mqtt_mock: MqttMockHAClient,
    setup_tasmota,
) -> None:
    """Test availability after MQTT disconnection."""
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["rl"][0] = 1
    await help_test_availability_when_connection_lost(
        menuai, mqtt_client_mock, mqtt_mock, Platform.SWITCH, config
    )


async def test_deep_sleep_availability_when_connection_lost(
    menuai: menuai,
    mqtt_client_mock: MqttMockPahoClient,
    mqtt_mock: MqttMockHAClient,
    setup_tasmota,
) -> None:
    """Test availability after MQTT disconnection."""
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["rl"][0] = 1
    await help_test_deep_sleep_availability_when_connection_lost(
        menuai, mqtt_client_mock, mqtt_mock, Platform.SWITCH, config
    )


async def test_availability(
    menuai: menuai, mqtt_mock: MqttMockHAClient, setup_tasmota
) -> None:
    """Test availability."""
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["rl"][0] = 1
    await help_test_availability(menuai, mqtt_mock, Platform.SWITCH, config)


async def test_deep_sleep_availability(
    menuai: menuai, mqtt_mock: MqttMockHAClient, setup_tasmota
) -> None:
    """Test availability."""
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["rl"][0] = 1
    await help_test_deep_sleep_availability(menuai, mqtt_mock, Platform.SWITCH, config)


async def test_availability_discovery_update(
    menuai: menuai, mqtt_mock: MqttMockHAClient, setup_tasmota
) -> None:
    """Test availability discovery update."""
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["rl"][0] = 1
    await help_test_availability_discovery_update(
        menuai, mqtt_mock, Platform.SWITCH, config
    )


async def test_availability_poll_state(
    menuai: menuai,
    mqtt_client_mock: MqttMockPahoClient,
    mqtt_mock: MqttMockHAClient,
    setup_tasmota,
) -> None:
    """Test polling after MQTT connection (re)established."""
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["rl"][0] = 1
    poll_topic = "tasmota_49A3BC/cmnd/STATE"
    await help_test_availability_poll_state(
        menuai, mqtt_client_mock, mqtt_mock, Platform.SWITCH, config, poll_topic, ""
    )


async def test_discovery_removal_switch(
    menuai: menuai,
    mqtt_mock: MqttMockHAClient,
    caplog: pytest.LogCaptureFixture,
    setup_tasmota,
) -> None:
    """Test removal of discovered switch."""
    config1 = copy.deepcopy(DEFAULT_CONFIG)
    config1["rl"][0] = 1
    config2 = copy.deepcopy(DEFAULT_CONFIG)
    config2["rl"][0] = 0

    await help_test_discovery_removal(
        menuai, mqtt_mock, caplog, Platform.SWITCH, config1, config2
    )


async def test_discovery_removal_relay_as_light(
    menuai: menuai,
    mqtt_mock: MqttMockHAClient,
    caplog: pytest.LogCaptureFixture,
    setup_tasmota,
) -> None:
    """Test removal of discovered relay as light."""
    config1 = copy.deepcopy(DEFAULT_CONFIG)
    config1["rl"][0] = 1
    config1["so"]["30"] = 0  # Disable MenuAI auto-discovery as light
    config2 = copy.deepcopy(DEFAULT_CONFIG)
    config2["rl"][0] = 1
    config2["so"]["30"] = 1  # Enforce MenuAI auto-discovery as light

    await help_test_discovery_removal(
        menuai, mqtt_mock, caplog, Platform.SWITCH, config1, config2
    )


async def test_discovery_update_unchanged_switch(
    menuai: menuai,
    mqtt_mock: MqttMockHAClient,
    caplog: pytest.LogCaptureFixture,
    setup_tasmota,
) -> None:
    """Test update of discovered switch."""
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["rl"][0] = 1
    with patch(
        "menuai.components.tasmota.switch.TasmotaSwitch.discovery_update"
    ) as discovery_update:
        await help_test_discovery_update_unchanged(
            menuai, mqtt_mock, caplog, Platform.SWITCH, config, discovery_update
        )


async def test_discovery_device_remove(
    menuai: menuai, mqtt_mock: MqttMockHAClient, setup_tasmota
) -> None:
    """Test device registry remove."""
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["rl"][0] = 1
    unique_id = f"{DEFAULT_CONFIG['mac']}_switch_relay_0"
    await help_test_discovery_device_remove(
        menuai, mqtt_mock, Platform.SWITCH, unique_id, config
    )


async def test_entity_id_update_subscriptions(
    menuai: menuai, mqtt_mock: MqttMockHAClient, setup_tasmota
) -> None:
    """Test MQTT subscriptions are managed when entity_id is updated."""
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["rl"][0] = 1
    topics = [
        get_topic_stat_result(config),
        get_topic_tele_state(config),
        get_topic_tele_will(config),
    ]
    await help_test_entity_id_update_subscriptions(
        menuai, mqtt_mock, Platform.SWITCH, config, topics
    )


async def test_entity_id_update_discovery_update(
    menuai: menuai, mqtt_mock: MqttMockHAClient, setup_tasmota
) -> None:
    """Test MQTT discovery update when entity_id is updated."""
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["rl"][0] = 1
    await help_test_entity_id_update_discovery_update(
        menuai, mqtt_mock, Platform.SWITCH, config
    )


async def test_no_device_name(
    menuai: menuai, mqtt_mock: MqttMockHAClient, setup_tasmota
) -> None:
    """Test name of switches when no device name is set.

    When the device name is not set, Tasmota uses friendly name 1 as device naem.
    This test ensures that case is handled correctly.
    """
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["dn"] = "Relay 1"
    config["fn"][0] = "Relay 1"
    config["fn"][1] = "Relay 2"
    config["rl"][0] = 1
    config["rl"][1] = 1
    mac = config["mac"]

    async_fire_mqtt_message(
        menuai,
        f"{DEFAULT_PREFIX}/{mac}/config",
        json.dumps(config),
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("switch.relay_1")
    assert state is not None
    assert state.attributes["friendly_name"] == "Relay 1"

    state = menuai.states.get("switch.relay_1_relay_2")
    assert state is not None
    assert state.attributes["friendly_name"] == "Relay 1 Relay 2"
