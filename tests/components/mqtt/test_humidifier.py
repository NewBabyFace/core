"""Test MQTT humidifiers."""

import copy
from typing import Any
from unittest.mock import patch

import pytest
from voluptuous.error import MultipleInvalid

from menuai.components import humidifier, mqtt
from menuai.components.humidifier import (
    ATTR_CURRENT_HUMIDITY,
    ATTR_HUMIDITY,
    ATTR_MODE,
    SERVICE_SET_HUMIDITY,
    SERVICE_SET_MODE,
    HumidifierAction,
)
from menuai.components.mqtt.const import CONF_CURRENT_HUMIDITY_TOPIC
from menuai.components.mqtt.humidifier import (
    CONF_MODE_COMMAND_TOPIC,
    CONF_MODE_STATE_TOPIC,
    CONF_TARGET_HUMIDITY_STATE_TOPIC,
    MQTT_HUMIDIFIER_ATTRIBUTES_BLOCKED,
)
from menuai.const import (
    ATTR_ASSUMED_STATE,
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    ENTITY_MATCH_ALL,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNKNOWN,
)
from menuai.core import menuai

from .common import (
    help_custom_config,
    help_test_availability_when_connection_lost,
    help_test_availability_without_topic,
    help_test_custom_availability_payload,
    help_test_default_availability_payload,
    help_test_discovery_broken,
    help_test_discovery_removal,
    help_test_discovery_update,
    help_test_discovery_update_attr,
    help_test_discovery_update_unchanged,
    help_test_encoding_subscribable_topics,
    help_test_entity_debug_info_message,
    help_test_entity_device_info_remove,
    help_test_entity_device_info_update,
    help_test_entity_device_info_with_connection,
    help_test_entity_device_info_with_identifier,
    help_test_entity_id_update_discovery_update,
    help_test_entity_id_update_subscriptions,
    help_test_publishing_with_custom_encoding,
    help_test_reloadable,
    help_test_setting_attribute_via_mqtt_json_message,
    help_test_setting_attribute_with_template,
    help_test_setting_blocked_attribute_via_mqtt_json_message,
    help_test_skipped_async_ha_write_state,
    help_test_unique_id,
    help_test_unload_config_entry_with_platform,
    help_test_update_with_json_attrs_bad_json,
    help_test_update_with_json_attrs_not_dict,
)

from tests.common import async_fire_mqtt_message
from tests.typing import MqttMockHAClientGenerator, MqttMockPahoClient

DEFAULT_CONFIG = {
    mqtt.DOMAIN: {
        humidifier.DOMAIN: {
            "name": "test",
            "state_topic": "state-topic",
            "command_topic": "command-topic",
            "target_humidity_command_topic": "humidity-command-topic",
        }
    }
}


async def async_turn_on(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Turn all or specified humidifier on."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}

    await menuai.services.async_call(
        humidifier.DOMAIN, SERVICE_TURN_ON, data, blocking=True
    )


async def async_turn_off(
    menuai: menuai, entity_id: str = ENTITY_MATCH_ALL
) -> None:
    """Turn all or specified humidier off."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}

    await menuai.services.async_call(
        humidifier.DOMAIN, SERVICE_TURN_OFF, data, blocking=True
    )


async def async_set_mode(
    menuai: menuai, entity_id: str = ENTITY_MATCH_ALL, mode: str | None = None
) -> None:
    """Set mode for all or specified humidifier."""
    data = {
        key: value
        for key, value in ((ATTR_ENTITY_ID, entity_id), (ATTR_MODE, mode))
        if value is not None
    }

    await menuai.services.async_call(
        humidifier.DOMAIN, SERVICE_SET_MODE, data, blocking=True
    )


async def async_set_humidity(
    menuai: menuai, entity_id: str = ENTITY_MATCH_ALL, humidity: int | None = None
) -> None:
    """Set target humidity for all or specified humidifier."""
    data = {
        key: value
        for key, value in ((ATTR_ENTITY_ID, entity_id), (ATTR_HUMIDITY, humidity))
        if value is not None
    }

    await menuai.services.async_call(
        humidifier.DOMAIN, SERVICE_SET_HUMIDITY, data, blocking=True
    )


@pytest.mark.parametrize(
    "menuai_config", [{mqtt.DOMAIN: {humidifier.DOMAIN: {"name": "test"}}}]
)
@pytest.mark.usefixtures("menuai")
async def test_fail_setup_if_no_command_topic(
    mqtt_mock_entry: MqttMockHAClientGenerator, caplog: pytest.LogCaptureFixture
) -> None:
    """Test if command fails with command topic."""
    assert await mqtt_mock_entry()
    assert "required key not provided" in caplog.text


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                humidifier.DOMAIN: {
                    "name": "test",
                    "action_topic": "action-topic",
                    "state_topic": "state-topic",
                    "command_topic": "command-topic",
                    "current_humidity_topic": "current-humidity-topic",
                    "payload_off": "StAtE_OfF",
                    "payload_on": "StAtE_On",
                    "target_humidity_state_topic": "humidity-state-topic",
                    "target_humidity_command_topic": "humidity-command-topic",
                    "mode_state_topic": "mode-state-topic",
                    "mode_command_topic": "mode-command-topic",
                    "modes": [
                        "auto",
                        "comfort",
                        "home",
                        "eco",
                        "sleep",
                        "baby",
                    ],
                    "payload_reset_humidity": "rEset_humidity",
                    "payload_reset_mode": "rEset_mode",
                }
            }
        }
    ],
)
async def test_controlling_state_via_topic(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the controlling state via topic."""
    await mqtt_mock_entry()

    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_UNKNOWN
    assert not state.attributes.get(ATTR_ASSUMED_STATE)
    assert not state.attributes.get(humidifier.ATTR_ACTION)

    async_fire_mqtt_message(menuai, "state-topic", "StAtE_On")
    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_ON
    assert not state.attributes.get(humidifier.ATTR_ACTION)

    async_fire_mqtt_message(menuai, "state-topic", "StAtE_OfF")
    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_OFF
    assert not state.attributes.get(humidifier.ATTR_ACTION)

    async_fire_mqtt_message(menuai, "humidity-state-topic", "0")
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_HUMIDITY) == 0

    async_fire_mqtt_message(menuai, "humidity-state-topic", "25")
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_HUMIDITY) == 25

    async_fire_mqtt_message(menuai, "humidity-state-topic", "50")
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_HUMIDITY) == 50

    async_fire_mqtt_message(menuai, "humidity-state-topic", "100")
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_HUMIDITY) == 100

    async_fire_mqtt_message(menuai, "humidity-state-topic", "101")
    assert "not a valid target humidity" in caplog.text
    caplog.clear()

    async_fire_mqtt_message(menuai, "humidity-state-topic", "invalid")
    assert "not a valid target humidity" in caplog.text
    caplog.clear()

    async_fire_mqtt_message(menuai, "mode-state-topic", "low")
    assert "not a valid mode" in caplog.text
    caplog.clear()

    async_fire_mqtt_message(menuai, "current-humidity-topic", "48")
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_CURRENT_HUMIDITY) == 48

    async_fire_mqtt_message(menuai, "current-humidity-topic", "101")
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_CURRENT_HUMIDITY) == 48

    async_fire_mqtt_message(menuai, "current-humidity-topic", "-1.6")
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_CURRENT_HUMIDITY) == 48

    async_fire_mqtt_message(menuai, "current-humidity-topic", "43.6")
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_CURRENT_HUMIDITY) == 44

    async_fire_mqtt_message(menuai, "current-humidity-topic", "invalid")
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_CURRENT_HUMIDITY) == 44

    async_fire_mqtt_message(menuai, "mode-state-topic", "auto")
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_MODE) == "auto"

    async_fire_mqtt_message(menuai, "mode-state-topic", "eco")
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_MODE) == "eco"

    async_fire_mqtt_message(menuai, "mode-state-topic", "baby")
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_MODE) == "baby"

    async_fire_mqtt_message(menuai, "mode-state-topic", "ModeUnknown")
    assert "not a valid mode" in caplog.text
    caplog.clear()

    async_fire_mqtt_message(menuai, "mode-state-topic", "rEset_mode")
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_MODE) is None

    async_fire_mqtt_message(menuai, "humidity-state-topic", "rEset_humidity")
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_HUMIDITY) is None

    async_fire_mqtt_message(menuai, "state-topic", "None")
    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_UNKNOWN
    assert not state.attributes.get(humidifier.ATTR_ACTION)

    # Turn un the humidifier
    async_fire_mqtt_message(menuai, "state-topic", "StAtE_On")
    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_ON
    assert not state.attributes.get(humidifier.ATTR_ACTION)

    async_fire_mqtt_message(menuai, "action-topic", HumidifierAction.DRYING.value)
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_ACTION) == HumidifierAction.DRYING

    async_fire_mqtt_message(menuai, "action-topic", HumidifierAction.HUMIDIFYING.value)
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_ACTION) == HumidifierAction.HUMIDIFYING

    async_fire_mqtt_message(menuai, "action-topic", HumidifierAction.HUMIDIFYING.value)
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_ACTION) == HumidifierAction.HUMIDIFYING

    async_fire_mqtt_message(menuai, "action-topic", "invalid_action")
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_ACTION) == HumidifierAction.HUMIDIFYING

    async_fire_mqtt_message(menuai, "state-topic", "StAtE_OfF")
    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_OFF
    assert state.attributes.get(humidifier.ATTR_ACTION) == HumidifierAction.OFF


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                humidifier.DOMAIN: {
                    "name": "test",
                    "action_topic": "action-topic",
                    "state_topic": "state-topic",
                    "command_topic": "command-topic",
                    "current_humidity_topic": "current-humidity-topic",
                    "target_humidity_state_topic": "humidity-state-topic",
                    "target_humidity_command_topic": "humidity-command-topic",
                    "mode_state_topic": "mode-state-topic",
                    "mode_command_topic": "mode-command-topic",
                    "modes": [
                        "auto",
                        "eco",
                        "baby",
                    ],
                    "current_humidity_template": "{{ value_json.val }}",
                    "action_template": "{{ value_json.val }}",
                    "state_value_template": "{{ value_json.val }}",
                    "target_humidity_state_template": "{{ value_json.val }}",
                    "mode_state_template": "{{ value_json.val }}",
                }
            }
        }
    ],
)
async def test_controlling_state_via_topic_and_json_message(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the controlling state via topic and JSON message."""
    await menuai.async_block_till_done()
    await mqtt_mock_entry()

    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_UNKNOWN
    assert not state.attributes.get(ATTR_ASSUMED_STATE)

    async_fire_mqtt_message(menuai, "state-topic", '{"val":"ON"}')
    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_ON

    async_fire_mqtt_message(menuai, "state-topic", '{"val":"OFF"}')
    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_OFF

    async_fire_mqtt_message(menuai, "humidity-state-topic", '{"val": 1}')
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_HUMIDITY) == 1

    async_fire_mqtt_message(menuai, "humidity-state-topic", '{"val": 100}')
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_HUMIDITY) == 100

    async_fire_mqtt_message(menuai, "humidity-state-topic", '{"val": "None"}')
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_HUMIDITY) is None

    async_fire_mqtt_message(menuai, "humidity-state-topic", '{"otherval": 100}')
    assert state.attributes.get(humidifier.ATTR_HUMIDITY) is None
    caplog.clear()

    async_fire_mqtt_message(menuai, "current-humidity-topic", '{"val": 1}')
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_CURRENT_HUMIDITY) == 1

    async_fire_mqtt_message(menuai, "current-humidity-topic", '{"val": 100}')
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_CURRENT_HUMIDITY) == 100

    async_fire_mqtt_message(menuai, "current-humidity-topic", '{"val": "None"}')
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_CURRENT_HUMIDITY) is None

    async_fire_mqtt_message(menuai, "current-humidity-topic", '{"otherval": 100}')
    assert state.attributes.get(humidifier.ATTR_CURRENT_HUMIDITY) is None
    caplog.clear()

    async_fire_mqtt_message(menuai, "mode-state-topic", '{"val": "low"}')
    assert "not a valid mode" in caplog.text
    caplog.clear()

    async_fire_mqtt_message(menuai, "mode-state-topic", '{"val": "auto"}')
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_MODE) == "auto"

    async_fire_mqtt_message(menuai, "mode-state-topic", '{"val": "eco"}')
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_MODE) == "eco"

    async_fire_mqtt_message(menuai, "mode-state-topic", '{"val": "baby"}')
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_MODE) == "baby"

    async_fire_mqtt_message(menuai, "mode-state-topic", '{"val": "None"}')
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_MODE) is None

    async_fire_mqtt_message(menuai, "mode-state-topic", '{"otherval": 100}')
    assert state.attributes.get(humidifier.ATTR_MODE) is None
    caplog.clear()

    async_fire_mqtt_message(menuai, "state-topic", '{"val": null}')
    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_UNKNOWN

    # Make sure the humidifier is ON
    async_fire_mqtt_message(menuai, "state-topic", '{"val":"ON"}')
    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_ON

    async_fire_mqtt_message(menuai, "action-topic", '{"val": "drying"}')
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_ACTION) == HumidifierAction.DRYING

    async_fire_mqtt_message(menuai, "action-topic", '{"val": "humidifying"}')
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_ACTION) == HumidifierAction.HUMIDIFYING

    async_fire_mqtt_message(menuai, "action-topic", '{"val": null}')
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_ACTION) == HumidifierAction.HUMIDIFYING

    async_fire_mqtt_message(menuai, "action-topic", '{"otherval": "idle"}')
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_ACTION) == HumidifierAction.HUMIDIFYING

    async_fire_mqtt_message(menuai, "action-topic", '{"val": "idle"}')
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_ACTION) == HumidifierAction.IDLE

    async_fire_mqtt_message(menuai, "action-topic", '{"val": "off"}')
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_ACTION) == HumidifierAction.OFF


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                humidifier.DOMAIN: {
                    "name": "test",
                    "state_topic": "shared-state-topic",
                    "command_topic": "command-topic",
                    "target_humidity_state_topic": "shared-state-topic",
                    "target_humidity_command_topic": "percentage-command-topic",
                    "mode_state_topic": "shared-state-topic",
                    "mode_command_topic": "mode-command-topic",
                    "modes": [
                        "auto",
                        "eco",
                        "baby",
                    ],
                    "state_value_template": "{{ value_json.state }}",
                    "target_humidity_state_template": "{{ value_json.humidity }}",
                    "mode_state_template": "{{ value_json.mode }}",
                }
            }
        }
    ],
)
async def test_controlling_state_via_topic_and_json_message_shared_topic(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the controlling state via topic and JSON message using a shared topic."""
    await mqtt_mock_entry()

    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_UNKNOWN
    assert not state.attributes.get(ATTR_ASSUMED_STATE)

    async_fire_mqtt_message(
        menuai,
        "shared-state-topic",
        '{"state":"ON","mode":"eco","humidity": 50}',
    )
    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_ON
    assert state.attributes.get(humidifier.ATTR_HUMIDITY) == 50
    assert state.attributes.get(humidifier.ATTR_MODE) == "eco"

    async_fire_mqtt_message(
        menuai,
        "shared-state-topic",
        '{"state":"ON","mode":"auto","humidity": 10}',
    )
    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_ON
    assert state.attributes.get(humidifier.ATTR_HUMIDITY) == 10
    assert state.attributes.get(humidifier.ATTR_MODE) == "auto"

    async_fire_mqtt_message(
        menuai,
        "shared-state-topic",
        '{"state":"OFF","mode":"auto","humidity": 0}',
    )
    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_OFF
    assert state.attributes.get(humidifier.ATTR_HUMIDITY) == 0
    assert state.attributes.get(humidifier.ATTR_MODE) == "auto"

    async_fire_mqtt_message(
        menuai,
        "shared-state-topic",
        '{"humidity": 100}',
    )
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_HUMIDITY) == 100
    assert state.attributes.get(humidifier.ATTR_MODE) == "auto"
    caplog.clear()


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                humidifier.DOMAIN: {
                    "name": "test",
                    "command_topic": "command-topic",
                    "payload_off": "StAtE_OfF",
                    "payload_on": "StAtE_On",
                    "target_humidity_command_topic": "humidity-command-topic",
                    "mode_command_topic": "mode-command-topic",
                    "modes": [
                        "eco",
                        "auto",
                        "baby",
                    ],
                }
            }
        }
    ],
)
async def test_sending_mqtt_commands_and_optimistic(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test optimistic mode without state topic."""
    mqtt_mock = await mqtt_mock_entry()

    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await async_turn_on(menuai, "humidifier.test")
    mqtt_mock.async_publish.assert_called_once_with(
        "command-topic", "StAtE_On", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_ON
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await async_turn_off(menuai, "humidifier.test")
    mqtt_mock.async_publish.assert_called_once_with(
        "command-topic", "StAtE_OfF", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_OFF
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    with pytest.raises(MultipleInvalid):
        await async_set_humidity(menuai, "humidifier.test", -1)

    with pytest.raises(MultipleInvalid):
        await async_set_humidity(menuai, "humidifier.test", 101)

    await async_set_humidity(menuai, "humidifier.test", 100)
    mqtt_mock.async_publish.assert_called_once_with(
        "humidity-command-topic", "100", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_HUMIDITY) == 100
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await async_set_humidity(menuai, "humidifier.test", 0)
    mqtt_mock.async_publish.assert_called_once_with(
        "humidity-command-topic", "0", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_HUMIDITY) == 0
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await async_set_mode(menuai, "humidifier.test", "low")
    assert "not a valid mode" in caplog.text
    caplog.clear()

    await async_set_mode(menuai, "humidifier.test", "auto")
    mqtt_mock.async_publish.assert_called_once_with(
        "mode-command-topic", "auto", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_MODE) == "auto"
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await async_set_mode(menuai, "humidifier.test", "eco")
    mqtt_mock.async_publish.assert_called_once_with(
        "mode-command-topic", "eco", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_MODE) == "eco"
    assert state.attributes.get(ATTR_ASSUMED_STATE)


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                humidifier.DOMAIN: {
                    "name": "test",
                    "command_topic": "command-topic",
                    "command_template": "state: {{ value }}",
                    "target_humidity_command_topic": "humidity-command-topic",
                    "target_humidity_command_template": "humidity: {{ value }}",
                    "mode_command_topic": "mode-command-topic",
                    "mode_command_template": "mode: {{ value }}",
                    "modes": [
                        "auto",
                        "eco",
                        "sleep",
                    ],
                }
            }
        }
    ],
)
async def test_sending_mqtt_command_templates_(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Testing command templates with optimistic mode without state topic."""
    mqtt_mock = await mqtt_mock_entry()

    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await async_turn_on(menuai, "humidifier.test")
    mqtt_mock.async_publish.assert_called_once_with(
        "command-topic", "state: ON", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_ON
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await async_turn_off(menuai, "humidifier.test")
    mqtt_mock.async_publish.assert_called_once_with(
        "command-topic", "state: OFF", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_OFF
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    with pytest.raises(MultipleInvalid):
        await async_set_humidity(menuai, "humidifier.test", -1)

    with pytest.raises(MultipleInvalid):
        await async_set_humidity(menuai, "humidifier.test", 101)

    await async_set_humidity(menuai, "humidifier.test", 100)
    mqtt_mock.async_publish.assert_called_once_with(
        "humidity-command-topic", "humidity: 100", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_HUMIDITY) == 100
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await async_set_humidity(menuai, "humidifier.test", 0)
    mqtt_mock.async_publish.assert_called_once_with(
        "humidity-command-topic", "humidity: 0", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_HUMIDITY) == 0
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await async_set_mode(menuai, "humidifier.test", "low")
    assert "not a valid mode" in caplog.text
    caplog.clear()

    await async_set_mode(menuai, "humidifier.test", "eco")
    mqtt_mock.async_publish.assert_called_once_with(
        "mode-command-topic", "mode: eco", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_MODE) == "eco"
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await async_set_mode(menuai, "humidifier.test", "auto")
    mqtt_mock.async_publish.assert_called_once_with(
        "mode-command-topic", "mode: auto", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = menuai.states.get("humidifier.test")
    assert state.attributes.get(humidifier.ATTR_MODE) == "auto"
    assert state.attributes.get(ATTR_ASSUMED_STATE)


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                humidifier.DOMAIN: {
                    "name": "test",
                    "state_topic": "state-topic",
                    "command_topic": "command-topic",
                    "target_humidity_state_topic": "humidity-state-topic",
                    "target_humidity_command_topic": "humidity-command-topic",
                    "mode_command_topic": "mode-command-topic",
                    "mode_state_topic": "mode-state-topic",
                    "modes": [
                        "auto",
                        "eco",
                        "baby",
                    ],
                    "optimistic": True,
                }
            }
        }
    ],
)
async def test_sending_mqtt_commands_and_explicit_optimistic(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test optimistic mode with state topic and turn on attributes."""
    mqtt_mock = await mqtt_mock_entry()

    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await async_turn_on(menuai, "humidifier.test")
    mqtt_mock.async_publish.assert_called_once_with("command-topic", "ON", 0, False)
    mqtt_mock.async_publish.reset_mock()
    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_ON
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await async_turn_off(menuai, "humidifier.test")
    mqtt_mock.async_publish.assert_called_once_with("command-topic", "OFF", 0, False)
    mqtt_mock.async_publish.reset_mock()
    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_OFF
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await async_set_humidity(menuai, "humidifier.test", 33)
    mqtt_mock.async_publish.assert_called_once_with(
        "humidity-command-topic", "33", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_OFF
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await async_set_humidity(menuai, "humidifier.test", 50)
    mqtt_mock.async_publish.assert_called_once_with(
        "humidity-command-topic", "50", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_OFF
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await async_set_humidity(menuai, "humidifier.test", 100)
    mqtt_mock.async_publish.assert_called_once_with(
        "humidity-command-topic", "100", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_OFF
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await async_set_humidity(menuai, "humidifier.test", 0)
    mqtt_mock.async_publish.assert_called_once_with(
        "humidity-command-topic", "0", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_OFF
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    with pytest.raises(MultipleInvalid):
        await async_set_humidity(menuai, "humidifier.test", 101)

    await async_set_mode(menuai, "humidifier.test", "low")
    assert "not a valid mode" in caplog.text
    caplog.clear()

    await async_set_mode(menuai, "humidifier.test", "eco")
    mqtt_mock.async_publish.assert_called_once_with(
        "mode-command-topic", "eco", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_OFF
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await async_set_mode(menuai, "humidifier.test", "baby")
    mqtt_mock.async_publish.assert_called_once_with(
        "mode-command-topic", "baby", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_OFF
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await async_set_mode(menuai, "humidifier.test", "freaking-high")
    assert "not a valid mode" in caplog.text
    caplog.clear()

    mqtt_mock.async_publish.reset_mock()
    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_OFF
    assert state.attributes.get(ATTR_ASSUMED_STATE)


@pytest.mark.parametrize(
    ("topic", "value", "attribute", "attribute_value"),
    [
        ("state_topic", "ON", None, "on"),
        (CONF_MODE_STATE_TOPIC, "auto", ATTR_MODE, "auto"),
        (CONF_TARGET_HUMIDITY_STATE_TOPIC, "45", ATTR_HUMIDITY, 45),
        (CONF_CURRENT_HUMIDITY_TOPIC, "39", ATTR_CURRENT_HUMIDITY, 39),
    ],
)
async def test_encoding_subscribable_topics(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    topic: str,
    value: str,
    attribute: str | None,
    attribute_value: Any,
) -> None:
    """Test handling of incoming encoded payload."""
    config: dict[str, Any] = copy.deepcopy(
        DEFAULT_CONFIG[mqtt.DOMAIN][humidifier.DOMAIN]
    )
    config["modes"] = ["eco", "auto"]
    config[CONF_MODE_COMMAND_TOPIC] = "humidifier/some_mode_command_topic"
    await help_test_encoding_subscribable_topics(
        menuai,
        mqtt_mock_entry,
        humidifier.DOMAIN,
        config,
        topic,
        value,
        attribute,
        attribute_value,
    )


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                humidifier.DOMAIN: {
                    "name": "test",
                    "command_topic": "command-topic",
                    "mode_command_topic": "mode-command-topic",
                    "target_humidity_command_topic": "humidity-command-topic",
                    "modes": [
                        "eco",
                        "baby",
                    ],
                }
            }
        }
    ],
)
async def test_attributes(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test attributes."""
    await mqtt_mock_entry()

    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(humidifier.ATTR_AVAILABLE_MODES) == [
        "eco",
        "baby",
    ]
    assert state.attributes.get(humidifier.ATTR_MIN_HUMIDITY) == 0
    assert state.attributes.get(humidifier.ATTR_MAX_HUMIDITY) == 100

    await async_turn_on(menuai, "humidifier.test")
    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_ON
    assert state.attributes.get(ATTR_ASSUMED_STATE)
    assert state.attributes.get(humidifier.ATTR_HUMIDITY) is None
    assert state.attributes.get(humidifier.ATTR_MODE) is None

    await async_turn_off(menuai, "humidifier.test")
    state = menuai.states.get("humidifier.test")
    assert state.state == STATE_OFF
    assert state.attributes.get(ATTR_ASSUMED_STATE)
    assert state.attributes.get(humidifier.ATTR_HUMIDITY) is None
    assert state.attributes.get(humidifier.ATTR_MODE) is None


@pytest.mark.parametrize(
    ("menuai_config", "valid"),
    [
        (  # test valid case 1
            {
                mqtt.DOMAIN: {
                    humidifier.DOMAIN: {
                        "name": "test",
                        "command_topic": "command-topic",
                        "target_humidity_command_topic": "humidity-command-topic",
                    }
                }
            },
            True,
        ),
        (  # test valid case 2
            {
                mqtt.DOMAIN: {
                    humidifier.DOMAIN: {
                        "name": "test",
                        "command_topic": "command-topic",
                        "target_humidity_command_topic": "humidity-command-topic",
                        "device_class": "humidifier",
                    }
                }
            },
            True,
        ),
        (  # test valid case 3
            {
                mqtt.DOMAIN: {
                    humidifier.DOMAIN: {
                        "name": "test",
                        "command_topic": "command-topic",
                        "target_humidity_command_topic": "humidity-command-topic",
                        "device_class": "dehumidifier",
                    }
                }
            },
            True,
        ),
        (  # test valid case 4
            {
                mqtt.DOMAIN: {
                    humidifier.DOMAIN: {
                        "name": "test",
                        "command_topic": "command-topic",
                        "target_humidity_command_topic": "humidity-command-topic",
                        "device_class": None,
                    }
                }
            },
            True,
        ),
        (  # test invalid device_class
            {
                mqtt.DOMAIN: {
                    humidifier.DOMAIN: {
                        "name": "test",
                        "command_topic": "command-topic",
                        "target_humidity_command_topic": "humidity-command-topic",
                        "device_class": "notsupporedSpeci@l",
                    }
                }
            },
            False,
        ),
        (  # test mode_command_topic without modes
            {
                mqtt.DOMAIN: {
                    humidifier.DOMAIN: {
                        "name": "test",
                        "command_topic": "command-topic",
                        "target_humidity_command_topic": "humidity-command-topic",
                        "mode_command_topic": "mode-command-topic",
                    }
                }
            },
            False,
        ),
        (  # test invalid humidity min max case 1
            {
                mqtt.DOMAIN: {
                    humidifier.DOMAIN: {
                        "name": "test",
                        "command_topic": "command-topic",
                        "target_humidity_command_topic": "humidity-command-topic",
                        "min_humidity": 0,
                        "max_humidity": 101,
                    }
                }
            },
            False,
        ),
        (  # test invalid humidity min max case 2
            {
                mqtt.DOMAIN: {
                    humidifier.DOMAIN: {
                        "name": "test",
                        "command_topic": "command-topic",
                        "target_humidity_command_topic": "humidity-command-topic",
                        "max_humidity": 20,
                        "min_humidity": 40,
                    }
                }
            },
            False,
        ),
        (  # test invalid mode, is reset payload
            {
                mqtt.DOMAIN: {
                    humidifier.DOMAIN: {
                        "name": "test",
                        "command_topic": "command-topic",
                        "target_humidity_command_topic": "humidity-command-topic",
                        "mode_command_topic": "mode-command-topic",
                        "modes": ["eco", "None"],
                    }
                }
            },
            False,
        ),
    ],
)
async def test_validity_configurations(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator, valid: bool
) -> None:
    """Test validity of configurations."""
    await mqtt_mock_entry()
    state = menuai.states.get("humidifier.test")
    assert (state is not None) == valid


@pytest.mark.parametrize(
    ("name", "menuai_config", "success", "features"),
    [
        (
            "test1",
            {
                mqtt.DOMAIN: {
                    humidifier.DOMAIN: {
                        "name": "test1",
                        "command_topic": "command-topic",
                        "target_humidity_command_topic": "humidity-command-topic",
                    }
                }
            },
            True,
            0,
        ),
        (
            "test2",
            {
                mqtt.DOMAIN: {
                    humidifier.DOMAIN: {
                        "name": "test2",
                        "command_topic": "command-topic",
                        "target_humidity_command_topic": "humidity-command-topic",
                        "mode_command_topic": "mode-command-topic",
                        "modes": ["eco", "auto"],
                    }
                }
            },
            True,
            humidifier.HumidifierEntityFeature.MODES,
        ),
        (
            "test3",
            {
                mqtt.DOMAIN: {
                    humidifier.DOMAIN: {
                        "name": "test3",
                        "command_topic": "command-topic",
                        "target_humidity_command_topic": "humidity-command-topic",
                    }
                }
            },
            True,
            0,
        ),
        (
            "test4",
            {
                mqtt.DOMAIN: {
                    humidifier.DOMAIN: {
                        "name": "test4",
                        "command_topic": "command-topic",
                        "target_humidity_command_topic": "humidity-command-topic",
                        "mode_command_topic": "mode-command-topic",
                        "modes": ["eco", "auto"],
                    }
                }
            },
            True,
            humidifier.HumidifierEntityFeature.MODES,
        ),
        (
            "test5",
            {
                mqtt.DOMAIN: {
                    humidifier.DOMAIN: {
                        "name": "test5",
                        "command_topic": "command-topic",
                    }
                }
            },
            False,
            None,
        ),
        (
            "test6",
            {
                mqtt.DOMAIN: {
                    humidifier.DOMAIN: {
                        "name": "test6",
                        "target_humidity_command_topic": "humidity-command-topic",
                    }
                }
            },
            False,
            None,
        ),
    ],
)
async def test_supported_features(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    name: str,
    success: bool,
    features: humidifier.HumidifierEntityFeature | None,
) -> None:
    """Test supported features."""
    await mqtt_mock_entry()
    state = menuai.states.get(f"humidifier.{name}")
    assert (state is not None) == success
    if success:
        assert state.attributes.get(ATTR_SUPPORTED_FEATURES) == features


@pytest.mark.parametrize("menuai_config", [DEFAULT_CONFIG])
async def test_availability_when_connection_lost(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test availability after MQTT disconnection."""
    await help_test_availability_when_connection_lost(
        menuai, mqtt_mock_entry, humidifier.DOMAIN
    )


@pytest.mark.parametrize("menuai_config", [DEFAULT_CONFIG])
async def test_availability_without_topic(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test availability without defined availability topic."""
    await help_test_availability_without_topic(
        menuai, mqtt_mock_entry, humidifier.DOMAIN, DEFAULT_CONFIG
    )


async def test_default_availability_payload(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test availability by default payload with defined topic."""
    await help_test_default_availability_payload(
        menuai,
        mqtt_mock_entry,
        humidifier.DOMAIN,
        DEFAULT_CONFIG,
        True,
        "state-topic",
        "1",
    )


async def test_custom_availability_payload(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test availability by custom payload with defined topic."""
    await help_test_custom_availability_payload(
        menuai,
        mqtt_mock_entry,
        humidifier.DOMAIN,
        DEFAULT_CONFIG,
        True,
        "state-topic",
        "1",
    )


async def test_setting_attribute_via_mqtt_json_message(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the setting of attribute via MQTT with JSON payload."""
    await help_test_setting_attribute_via_mqtt_json_message(
        menuai, mqtt_mock_entry, humidifier.DOMAIN, DEFAULT_CONFIG
    )


async def test_setting_blocked_attribute_via_mqtt_json_message(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the setting of attribute via MQTT with JSON payload."""
    await help_test_setting_blocked_attribute_via_mqtt_json_message(
        menuai,
        mqtt_mock_entry,
        humidifier.DOMAIN,
        DEFAULT_CONFIG,
        MQTT_HUMIDIFIER_ATTRIBUTES_BLOCKED,
    )


async def test_setting_attribute_with_template(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the setting of attribute via MQTT with JSON payload."""
    await help_test_setting_attribute_with_template(
        menuai, mqtt_mock_entry, humidifier.DOMAIN, DEFAULT_CONFIG
    )


async def test_update_with_json_attrs_not_dict(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test attributes get extracted from a JSON result."""
    await help_test_update_with_json_attrs_not_dict(
        menuai, mqtt_mock_entry, caplog, humidifier.DOMAIN, DEFAULT_CONFIG
    )


async def test_update_with_json_attrs_bad_json(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test attributes get extracted from a JSON result."""
    await help_test_update_with_json_attrs_bad_json(
        menuai, mqtt_mock_entry, caplog, humidifier.DOMAIN, DEFAULT_CONFIG
    )


async def test_discovery_update_attr(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test update of discovered MQTTAttributes."""
    await help_test_discovery_update_attr(
        menuai, mqtt_mock_entry, humidifier.DOMAIN, DEFAULT_CONFIG
    )


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                humidifier.DOMAIN: [
                    {
                        "name": "Test 1",
                        "state_topic": "test-topic",
                        "command_topic": "test_topic",
                        "target_humidity_command_topic": "humidity-command-topic",
                        "unique_id": "TOTALLY_UNIQUE",
                    },
                    {
                        "name": "Test 2",
                        "state_topic": "test-topic",
                        "command_topic": "test_topic",
                        "target_humidity_command_topic": "humidity-command-topic",
                        "unique_id": "TOTALLY_UNIQUE",
                    },
                ]
            }
        }
    ],
)
async def test_unique_id(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test unique_id option only creates one fan per id."""
    await help_test_unique_id(menuai, mqtt_mock_entry, humidifier.DOMAIN)


async def test_discovery_removal_humidifier(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test removal of discovered humidifier."""
    data = '{ "name": "test", "command_topic": "test_topic", "target_humidity_command_topic": "test-topic2" }'
    await help_test_discovery_removal(menuai, mqtt_mock_entry, humidifier.DOMAIN, data)


async def test_discovery_update_humidifier(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test update of discovered humidifier."""
    config1 = {
        "name": "Beer",
        "command_topic": "test_topic",
        "target_humidity_command_topic": "test-topic2",
    }
    config2 = {
        "name": "Milk",
        "command_topic": "test_topic",
        "target_humidity_command_topic": "test-topic2",
    }
    await help_test_discovery_update(
        menuai, mqtt_mock_entry, humidifier.DOMAIN, config1, config2
    )


async def test_discovery_update_unchanged_humidifier(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test update of discovered humidifier."""
    data1 = '{ "name": "Beer", "command_topic": "test_topic", "target_humidity_command_topic": "test-topic2" }'
    with patch(
        "menuai.components.mqtt.fan.MqttFan.discovery_update"
    ) as discovery_update:
        await help_test_discovery_update_unchanged(
            menuai, mqtt_mock_entry, humidifier.DOMAIN, data1, discovery_update
        )


@pytest.mark.no_fail_on_log_exception
async def test_discovery_broken(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test handling of bad discovery message."""
    data1 = '{ "name": "Beer" }'
    data2 = '{ "name": "Milk", "command_topic": "test_topic", "target_humidity_command_topic": "test-topic2" }'
    await help_test_discovery_broken(
        menuai, mqtt_mock_entry, humidifier.DOMAIN, data1, data2
    )


async def test_entity_device_info_with_connection(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT fan device registry integration."""
    await help_test_entity_device_info_with_connection(
        menuai, mqtt_mock_entry, humidifier.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_device_info_with_identifier(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT fan device registry integration."""
    await help_test_entity_device_info_with_identifier(
        menuai, mqtt_mock_entry, humidifier.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_device_info_update(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test device registry update."""
    await help_test_entity_device_info_update(
        menuai, mqtt_mock_entry, humidifier.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_device_info_remove(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test device registry remove."""
    await help_test_entity_device_info_remove(
        menuai, mqtt_mock_entry, humidifier.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_id_update_subscriptions(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT subscriptions are managed when entity_id is updated."""
    await help_test_entity_id_update_subscriptions(
        menuai, mqtt_mock_entry, humidifier.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_id_update_discovery_update(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT discovery update when entity_id is updated."""
    await help_test_entity_id_update_discovery_update(
        menuai, mqtt_mock_entry, humidifier.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_debug_info_message(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT debug info."""
    await help_test_entity_debug_info_message(
        menuai,
        mqtt_mock_entry,
        humidifier.DOMAIN,
        DEFAULT_CONFIG,
        humidifier.SERVICE_TURN_ON,
    )


@pytest.mark.parametrize(
    ("service", "topic", "parameters", "payload", "template"),
    [
        (
            humidifier.SERVICE_TURN_ON,
            "command_topic",
            None,
            "ON",
            None,
        ),
        (
            humidifier.SERVICE_TURN_OFF,
            "command_topic",
            None,
            "OFF",
            None,
        ),
        (
            humidifier.SERVICE_SET_MODE,
            "mode_command_topic",
            {humidifier.ATTR_MODE: "eco"},
            "eco",
            "mode_command_template",
        ),
        (
            humidifier.SERVICE_SET_HUMIDITY,
            "target_humidity_command_topic",
            {humidifier.ATTR_HUMIDITY: "45"},
            45,
            "target_humidity_command_template",
        ),
    ],
)
async def test_publishing_with_custom_encoding(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
    service: str,
    topic: str,
    parameters: dict[str, Any],
    payload: str,
    template: str | None,
) -> None:
    """Test publishing MQTT payload with different encoding."""
    domain = humidifier.DOMAIN
    config: dict[str, Any] = copy.deepcopy(DEFAULT_CONFIG)
    if topic == "mode_command_topic":
        config[mqtt.DOMAIN][domain]["modes"] = ["auto", "eco"]

    await help_test_publishing_with_custom_encoding(
        menuai,
        mqtt_mock_entry,
        caplog,
        domain,
        config,
        service,
        topic,
        parameters,
        payload,
        template,
    )


async def test_reloadable(
    menuai: menuai, mqtt_client_mock: MqttMockPahoClient
) -> None:
    """Test reloading the MQTT platform."""
    domain = humidifier.DOMAIN
    config = DEFAULT_CONFIG
    await help_test_reloadable(menuai, mqtt_client_mock, domain, config)


@pytest.mark.parametrize(
    "menuai_config",
    [DEFAULT_CONFIG, {"mqtt": [DEFAULT_CONFIG["mqtt"]]}],
    ids=["platform_key", "listed"],
)
async def test_setup_manual_entity_from_yaml(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test setup manual configured MQTT entity."""
    await mqtt_mock_entry()
    platform = humidifier.DOMAIN
    assert menuai.states.get(f"{platform}.test")


async def test_unload_config_entry(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test unloading the config entry."""
    domain = humidifier.DOMAIN
    config = DEFAULT_CONFIG
    await help_test_unload_config_entry_with_platform(
        menuai, mqtt_mock_entry, domain, config
    )


@pytest.mark.parametrize(
    "menuai_config",
    [
        help_custom_config(
            humidifier.DOMAIN,
            DEFAULT_CONFIG,
            (
                {
                    "availability_topic": "availability-topic",
                    "json_attributes_topic": "json-attributes-topic",
                    "action_topic": "action-topic",
                    "target_humidity_state_topic": "target-humidity-state-topic",
                    "current_humidity_topic": "current-humidity-topic",
                    "mode_command_topic": "mode-command-topic",
                    "mode_state_topic": "mode-state-topic",
                    "modes": [
                        "comfort",
                        "eco",
                    ],
                },
            ),
        )
    ],
)
@pytest.mark.parametrize(
    ("topic", "payload1", "payload2"),
    [
        ("availability-topic", "online", "offline"),
        ("json-attributes-topic", '{"attr1": "val1"}', '{"attr1": "val2"}'),
        ("state-topic", "ON", "OFF"),
        ("action-topic", "idle", "humidifying"),
        ("current-humidity-topic", "31", "32"),
        ("target-humidity-state-topic", "30", "40"),
        ("mode-state-topic", "comfort", "eco"),
    ],
)
async def test_skipped_async_ha_write_state(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    topic: str,
    payload1: str,
    payload2: str,
) -> None:
    """Test a write state command is only called when there is change."""
    await mqtt_mock_entry()
    await help_test_skipped_async_ha_write_state(menuai, topic, payload1, payload2)


VALUE_TEMPLATES = {
    "state_value_template": "state_topic",
    "action_template": "action_topic",
    "mode_state_template": "mode_state_topic",
    "current_humidity_template": "current_humidity_topic",
    "target_humidity_state_template": "target_humidity_state_topic",
}


@pytest.mark.parametrize(
    "menuai_config",
    [
        help_custom_config(
            humidifier.DOMAIN,
            DEFAULT_CONFIG,
            (
                {
                    "mode_command_topic": "preset-mode-command-topic",
                    "modes": [
                        "auto",
                    ],
                    topic: "test-topic",
                    value_template: "{{ value_json.some_var * 1 }}",
                },
            ),
        )
        for value_template, topic in VALUE_TEMPLATES.items()
    ],
    ids=VALUE_TEMPLATES,
)
async def test_value_template_fails(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the rendering of MQTT value template fails."""
    await mqtt_mock_entry()
    async_fire_mqtt_message(menuai, "test-topic", '{"some_var": null }')
    assert (
        "TypeError: unsupported operand type(s) for *: 'NoneType' and 'int' rendering template"
        in caplog.text
    )
