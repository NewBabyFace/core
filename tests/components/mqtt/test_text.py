"""The tests for the MQTT text platform."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from menuai.components import mqtt, text
from menuai.const import ATTR_ASSUMED_STATE, ATTR_ENTITY_ID, STATE_UNKNOWN
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
    mqtt.DOMAIN: {text.DOMAIN: {"name": "test", "command_topic": "test-topic"}}
}


async def async_set_value(
    menuai: menuai, entity_id: str, value: str | None
) -> None:
    """Set input_text to value."""
    await menuai.services.async_call(
        text.DOMAIN,
        text.SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, text.ATTR_VALUE: value},
        blocking=True,
    )


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                text.DOMAIN: {
                    "name": "test",
                    "state_topic": "state-topic",
                    "command_topic": "command-topic",
                    "mode": "password",
                }
            }
        }
    ],
)
async def test_controlling_state_via_topic(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the controlling state via topic."""
    await mqtt_mock_entry()

    state = menuai.states.get("text.test")
    assert state.state == STATE_UNKNOWN
    assert state.attributes[text.ATTR_MODE] == "password"
    assert not state.attributes.get(ATTR_ASSUMED_STATE)

    async_fire_mqtt_message(menuai, "state-topic", "some state")

    state = menuai.states.get("text.test")
    assert state.state == "some state"

    async_fire_mqtt_message(menuai, "state-topic", "some other state")

    state = menuai.states.get("text.test")
    assert state.state == "some other state"

    async_fire_mqtt_message(menuai, "state-topic", "")

    state = menuai.states.get("text.test")
    assert state.state == ""


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                text.DOMAIN: {
                    "name": "test",
                    "state_topic": "state-topic",
                    "command_topic": "command-topic",
                    "min": 5,
                    "max": 5,
                }
            }
        }
    ],
)
async def test_forced_text_length(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test a text entity that only allows a fixed length."""
    await mqtt_mock_entry()

    state = menuai.states.get("text.test")
    assert state.state == STATE_UNKNOWN
    assert not state.attributes.get(ATTR_ASSUMED_STATE)

    async_fire_mqtt_message(menuai, "state-topic", "12345")
    state = menuai.states.get("text.test")
    assert state.state == "12345"

    caplog.clear()
    # Text too long
    async_fire_mqtt_message(menuai, "state-topic", "123456")
    state = menuai.states.get("text.test")
    assert state.state == "12345"
    assert (
        "Entity text.test provides state 123456 "
        "which is too long (maximum length 5)" in caplog.text
    )

    caplog.clear()
    # Text too short
    async_fire_mqtt_message(menuai, "state-topic", "1")
    state = menuai.states.get("text.test")
    assert state.state == "12345"
    assert (
        "Entity text.test provides state 1 "
        "which is too short (minimum length 5)" in caplog.text
    )
    # Valid update
    async_fire_mqtt_message(menuai, "state-topic", "54321")
    state = menuai.states.get("text.test")
    assert state.state == "54321"


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                text.DOMAIN: {
                    "name": "test",
                    "state_topic": "state-topic",
                    "command_topic": "command-topic",
                    "mode": "text",
                    "min": 2,
                    "max": 10,
                    "pattern": "(y|n)",
                }
            }
        }
    ],
)
async def test_controlling_validation_state_via_topic(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the validation of a received state."""
    await mqtt_mock_entry()

    state = menuai.states.get("text.test")
    assert state.state == STATE_UNKNOWN
    assert state.attributes[text.ATTR_MODE] == "text"

    async_fire_mqtt_message(menuai, "state-topic", "yes")
    state = menuai.states.get("text.test")
    assert state.state == "yes"

    # test pattern error
    caplog.clear()
    async_fire_mqtt_message(menuai, "state-topic", "other")
    await menuai.async_block_till_done()
    assert (
        "Entity text.test provides state other which does not match expected pattern (y|n)"
        in caplog.text
    )
    state = menuai.states.get("text.test")
    assert state.state == "yes"

    # test text size to large
    caplog.clear()
    async_fire_mqtt_message(menuai, "state-topic", "yesyesyesyes")
    await menuai.async_block_till_done()
    assert (
        "Entity text.test provides state yesyesyesyes which is too long (maximum length 10)"
        in caplog.text
    )
    state = menuai.states.get("text.test")
    assert state.state == "yes"

    # test text size to small
    caplog.clear()
    async_fire_mqtt_message(menuai, "state-topic", "y")
    await menuai.async_block_till_done()
    assert (
        "Entity text.test provides state y which is too short (minimum length 2)"
        in caplog.text
    )
    state = menuai.states.get("text.test")
    assert state.state == "yes"

    # test with valid text
    async_fire_mqtt_message(menuai, "state-topic", "no")
    await menuai.async_block_till_done()
    state = menuai.states.get("text.test")
    assert state.state == "no"


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                text.DOMAIN: {
                    "name": "test",
                    "command_topic": "command-topic",
                    "min": 20,
                    "max": 10,
                }
            }
        }
    ],
)
async def test_attribute_validation_max_greater_then_min(
    mqtt_mock_entry: MqttMockHAClientGenerator, caplog: pytest.LogCaptureFixture
) -> None:
    """Test the validation of min and max configuration attributes."""
    assert await mqtt_mock_entry()
    assert "text length min must be <= max" in caplog.text


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                text.DOMAIN: {
                    "name": "test",
                    "command_topic": "command-topic",
                    "min": 20,
                    "max": 257,
                }
            }
        }
    ],
)
async def test_attribute_validation_max_not_greater_then_max_state_length(
    mqtt_mock_entry: MqttMockHAClientGenerator, caplog: pytest.LogCaptureFixture
) -> None:
    """Test the max value of of max configuration attribute."""
    assert await mqtt_mock_entry()
    assert "max text length must be <= 255" in caplog.text


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                text.DOMAIN: {
                    "name": "test",
                    "command_topic": "command-topic",
                    "state_topic": "state-topic",
                }
            }
        }
    ],
)
async def test_validation_payload_greater_then_max_state_length(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the max value of of max configuration attribute."""
    assert await mqtt_mock_entry()

    state = menuai.states.get("text.test")
    assert state.state == STATE_UNKNOWN

    async_fire_mqtt_message(menuai, "state-topic", "".join("x" for _ in range(310)))

    assert "Cannot update state for entity text.test" in caplog.text


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                text.DOMAIN: {
                    "name": "test",
                    "command_topic": "command-topic",
                    "qos": "2",
                }
            }
        }
    ],
)
async def test_sending_mqtt_commands_and_optimistic(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the sending MQTT commands in optimistic mode."""
    mqtt_mock = await mqtt_mock_entry()

    state = menuai.states.get("text.test")
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await async_set_value(menuai, "text.test", "some other state")
    await menuai.async_block_till_done()

    mqtt_mock.async_publish.assert_called_once_with(
        "command-topic", "some other state", 2, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = menuai.states.get("text.test")
    assert state.state == "some other state"

    await async_set_value(menuai, "text.test", "some new state")

    mqtt_mock.async_publish.assert_called_once_with(
        "command-topic", "some new state", 2, False
    )
    state = menuai.states.get("text.test")
    assert state.state == "some new state"


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                text.DOMAIN: {
                    "name": "test",
                    "command_topic": "command-topic",
                    "mode": "text",
                    "min": 2,
                    "max": 10,
                    "pattern": "(y|n)",
                }
            }
        }
    ],
)
async def test_set_text_validation(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the initial state in optimistic mode."""
    await mqtt_mock_entry()

    state = menuai.states.get("text.test")
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    # text too long
    with pytest.raises(ValueError):
        await async_set_value(menuai, "text.test", "yes yes yes yes")

    # text too short
    with pytest.raises(ValueError):
        await async_set_value(menuai, "text.test", "y")

    # text not matching pattern
    with pytest.raises(ValueError):
        await async_set_value(menuai, "text.test", "other")

    await async_set_value(menuai, "text.test", "no")
    state = menuai.states.get("text.test")
    assert state.state == "no"


@pytest.mark.parametrize("menuai_config", [DEFAULT_CONFIG])
async def test_availability_when_connection_lost(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test availability after MQTT disconnection."""
    await help_test_availability_when_connection_lost(
        menuai, mqtt_mock_entry, text.DOMAIN
    )


@pytest.mark.parametrize("menuai_config", [DEFAULT_CONFIG])
async def test_availability_without_topic(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test availability without defined availability topic."""
    await help_test_availability_without_topic(
        menuai, mqtt_mock_entry, text.DOMAIN, DEFAULT_CONFIG
    )


async def test_default_availability_payload(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test availability by default payload with defined topic."""
    config = {
        mqtt.DOMAIN: {
            text.DOMAIN: {
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
            }
        }
    }
    await help_test_default_availability_payload(
        menuai, mqtt_mock_entry, text.DOMAIN, config, True, "state-topic", "some state"
    )


async def test_custom_availability_payload(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test availability by custom payload with defined topic."""
    config = {
        mqtt.DOMAIN: {
            text.DOMAIN: {
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
            }
        }
    }

    await help_test_custom_availability_payload(
        menuai, mqtt_mock_entry, text.DOMAIN, config, True, "state-topic", "1"
    )


async def test_setting_attribute_via_mqtt_json_message(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the setting of attribute via MQTT with JSON payload."""
    await help_test_setting_attribute_via_mqtt_json_message(
        menuai, mqtt_mock_entry, text.DOMAIN, DEFAULT_CONFIG
    )


async def test_setting_blocked_attribute_via_mqtt_json_message(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the setting of attribute via MQTT with JSON payload."""
    await help_test_setting_blocked_attribute_via_mqtt_json_message(
        menuai, mqtt_mock_entry, text.DOMAIN, DEFAULT_CONFIG, None
    )


async def test_setting_attribute_with_template(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the setting of attribute via MQTT with JSON payload."""
    await help_test_setting_attribute_with_template(
        menuai, mqtt_mock_entry, text.DOMAIN, DEFAULT_CONFIG
    )


async def test_update_with_json_attrs_not_dict(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test attributes get extracted from a JSON result."""
    await help_test_update_with_json_attrs_not_dict(
        menuai, mqtt_mock_entry, caplog, text.DOMAIN, DEFAULT_CONFIG
    )


async def test_update_with_json_attrs_bad_json(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test attributes get extracted from a JSON result."""
    await help_test_update_with_json_attrs_bad_json(
        menuai, mqtt_mock_entry, caplog, text.DOMAIN, DEFAULT_CONFIG
    )


async def test_discovery_update_attr(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test update of discovered MQTTAttributes."""
    await help_test_discovery_update_attr(
        menuai, mqtt_mock_entry, text.DOMAIN, DEFAULT_CONFIG
    )


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                text.DOMAIN: [
                    {
                        "name": "Test 1",
                        "state_topic": "test-topic",
                        "command_topic": "command-topic",
                        "unique_id": "TOTALLY_UNIQUE",
                    },
                    {
                        "name": "Test 2",
                        "state_topic": "test-topic",
                        "command_topic": "command-topic",
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
    """Test unique id option only creates one text per unique_id."""
    await help_test_unique_id(menuai, mqtt_mock_entry, text.DOMAIN)


async def test_discovery_removal_text(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test removal of discovered text entity."""
    data = (
        '{ "name": "test",'
        '  "state_topic": "test_topic",'
        '  "command_topic": "test_topic" }'
    )
    await help_test_discovery_removal(menuai, mqtt_mock_entry, text.DOMAIN, data)


async def test_discovery_text_update(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test update of discovered text entity."""
    config1 = {
        "name": "Beer",
        "command_topic": "command-topic",
        "state_topic": "state-topic",
    }
    config2 = {
        "name": "Milk",
        "command_topic": "command-topic",
        "state_topic": "state-topic",
    }

    await help_test_discovery_update(
        menuai, mqtt_mock_entry, text.DOMAIN, config1, config2
    )


async def test_discovery_update_unchanged_update(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test update of discovered update."""
    data1 = '{ "name": "Beer", "state_topic": "text-topic", "command_topic": "command-topic"}'
    with patch(
        "menuai.components.mqtt.text.MqttTextEntity.discovery_update"
    ) as discovery_update:
        await help_test_discovery_update_unchanged(
            menuai, mqtt_mock_entry, text.DOMAIN, data1, discovery_update
        )


async def test_discovery_update_text(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test update of discovered text entity."""
    config1 = {"name": "Beer", "command_topic": "cmd-topic1"}
    config2 = {"name": "Milk", "command_topic": "cmd-topic2"}
    await help_test_discovery_update(
        menuai, mqtt_mock_entry, text.DOMAIN, config1, config2
    )


async def test_discovery_update_unchanged_climate(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test update of discovered text entity."""
    data1 = '{ "name": "Beer", "command_topic": "cmd-topic" }'
    with patch(
        "menuai.components.mqtt.text.MqttTextEntity.discovery_update"
    ) as discovery_update:
        await help_test_discovery_update_unchanged(
            menuai, mqtt_mock_entry, text.DOMAIN, data1, discovery_update
        )


@pytest.mark.no_fail_on_log_exception
async def test_discovery_broken(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test handling of bad discovery message."""
    data1 = '{ "name": "Beer" }'
    data2 = (
        '{ "name": "Milk",'
        '  "state_topic": "test_topic",'
        '  "command_topic": "test_topic" }'
    )
    await help_test_discovery_broken(menuai, mqtt_mock_entry, text.DOMAIN, data1, data2)


async def test_entity_device_info_with_connection(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT text device registry integration."""
    await help_test_entity_device_info_with_connection(
        menuai, mqtt_mock_entry, text.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_device_info_with_identifier(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT text device registry integration."""
    await help_test_entity_device_info_with_identifier(
        menuai, mqtt_mock_entry, text.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_device_info_update(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test device registry update."""
    await help_test_entity_device_info_update(
        menuai, mqtt_mock_entry, text.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_device_info_remove(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test device registry remove."""
    await help_test_entity_device_info_remove(
        menuai, mqtt_mock_entry, text.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_id_update_subscriptions(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT subscriptions are managed when entity_id is updated."""
    await help_test_entity_id_update_subscriptions(
        menuai, mqtt_mock_entry, text.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_id_update_discovery_update(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT discovery update when entity_id is updated."""
    await help_test_entity_id_update_discovery_update(
        menuai, mqtt_mock_entry, text.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_debug_info_message(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT debug info."""
    await help_test_entity_debug_info_message(
        menuai, mqtt_mock_entry, text.DOMAIN, DEFAULT_CONFIG, None
    )


@pytest.mark.parametrize(
    ("service", "topic", "parameters", "payload", "template"),
    [
        (
            text.SERVICE_SET_VALUE,
            "command_topic",
            {text.ATTR_VALUE: "some text"},
            "some text",
            "command_template",
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
    domain = text.DOMAIN
    config = DEFAULT_CONFIG

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
    domain = text.DOMAIN
    config = DEFAULT_CONFIG
    await help_test_reloadable(menuai, mqtt_client_mock, domain, config)


@pytest.mark.parametrize(
    ("topic", "value", "attribute", "attribute_value"),
    [
        ("state_topic", "some text", None, "some text"),
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
    await help_test_encoding_subscribable_topics(
        menuai,
        mqtt_mock_entry,
        text.DOMAIN,
        DEFAULT_CONFIG[mqtt.DOMAIN][text.DOMAIN],
        topic,
        value,
        attribute,
        attribute_value,
    )


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
    platform = text.DOMAIN
    assert menuai.states.get(f"{platform}.test")


async def test_unload_entry(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test unloading the config entry."""
    domain = text.DOMAIN
    config = DEFAULT_CONFIG
    await help_test_unload_config_entry_with_platform(
        menuai, mqtt_mock_entry, domain, config
    )


@pytest.mark.parametrize(
    "menuai_config",
    [
        help_custom_config(
            text.DOMAIN,
            DEFAULT_CONFIG,
            (
                {
                    "state_topic": "test-topic",
                    "availability_topic": "availability-topic",
                    "json_attributes_topic": "json-attributes-topic",
                },
            ),
        )
    ],
)
@pytest.mark.parametrize(
    ("topic", "payload1", "payload2"),
    [
        ("test-topic", "My original text", "Changed text"),
        ("availability-topic", "online", "offline"),
        ("json-attributes-topic", '{"attr1": "val1"}', '{"attr1": "val2"}'),
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


@pytest.mark.parametrize(
    "menuai_config",
    [
        help_custom_config(
            text.DOMAIN,
            DEFAULT_CONFIG,
            (
                {
                    "state_topic": "test-topic",
                    "value_template": "{{ value_json.some_var * 1 }}",
                },
            ),
        )
    ],
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
