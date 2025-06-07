"""The tests for the MQTT button platform."""

import copy
from typing import Any
from unittest.mock import patch

import pytest

from menuai.components import button, mqtt
from menuai.const import ATTR_ENTITY_ID, ATTR_FRIENDLY_NAME, STATE_UNKNOWN
from menuai.core import menuai

from .common import (
    help_test_availability_when_connection_lost,
    help_test_availability_without_topic,
    help_test_custom_availability_payload,
    help_test_default_availability_payload,
    help_test_discovery_broken,
    help_test_discovery_removal,
    help_test_discovery_update,
    help_test_discovery_update_attr,
    help_test_discovery_update_unchanged,
    help_test_entity_debug_info_message,
    help_test_entity_device_info_remove,
    help_test_entity_device_info_update,
    help_test_entity_device_info_with_connection,
    help_test_entity_device_info_with_identifier,
    help_test_entity_icon_and_entity_picture,
    help_test_entity_id_update_discovery_update,
    help_test_entity_name,
    help_test_publishing_with_custom_encoding,
    help_test_reloadable,
    help_test_setting_attribute_via_mqtt_json_message,
    help_test_setting_attribute_with_template,
    help_test_setting_blocked_attribute_via_mqtt_json_message,
    help_test_unique_id,
    help_test_unload_config_entry_with_platform,
    help_test_update_with_json_attrs_bad_json,
    help_test_update_with_json_attrs_not_dict,
)

from tests.typing import MqttMockHAClientGenerator, MqttMockPahoClient

DEFAULT_CONFIG = {
    mqtt.DOMAIN: {button.DOMAIN: {"name": "test", "command_topic": "test-topic"}}
}


@pytest.mark.freeze_time("2021-11-08 13:31:44+00:00")
@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                button.DOMAIN: {
                    "command_topic": "command-topic",
                    "name": "test",
                    "object_id": "test_button",
                    "payload_press": "beer press",
                    "qos": "2",
                }
            }
        }
    ],
)
async def test_sending_mqtt_commands(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the sending MQTT commands."""
    mqtt_mock = await mqtt_mock_entry()

    state = menuai.states.get("button.test_button")
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == "test"

    await menuai.services.async_call(
        button.DOMAIN,
        button.SERVICE_PRESS,
        {ATTR_ENTITY_ID: "button.test_button"},
        blocking=True,
    )

    mqtt_mock.async_publish.assert_called_once_with(
        "command-topic", "beer press", 2, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = menuai.states.get("button.test_button")
    assert state.state == "2021-11-08T13:31:44+00:00"


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                button.DOMAIN: {
                    "command_topic": "command-topic",
                    "command_template": '{ "{{ value }}": "{{ entity_id }}" }',
                    "name": "test",
                    "payload_press": "milky_way_press",
                }
            }
        }
    ],
)
async def test_command_template(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the sending of MQTT commands through a command template."""
    mqtt_mock = await mqtt_mock_entry()

    state = menuai.states.get("button.test")
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == "test"

    await menuai.services.async_call(
        button.DOMAIN,
        button.SERVICE_PRESS,
        {ATTR_ENTITY_ID: "button.test"},
        blocking=True,
    )

    mqtt_mock.async_publish.assert_called_once_with(
        "command-topic", '{ "milky_way_press": "button.test" }', 0, False
    )
    mqtt_mock.async_publish.reset_mock()


@pytest.mark.parametrize("menuai_config", [DEFAULT_CONFIG])
async def test_availability_when_connection_lost(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test availability after MQTT disconnection."""
    await help_test_availability_when_connection_lost(
        menuai, mqtt_mock_entry, button.DOMAIN
    )


@pytest.mark.parametrize("menuai_config", [DEFAULT_CONFIG])
async def test_availability_without_topic(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test availability without defined availability topic."""
    await help_test_availability_without_topic(
        menuai, mqtt_mock_entry, button.DOMAIN, DEFAULT_CONFIG
    )


async def test_default_availability_payload(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test availability by default payload with defined topic."""
    config = {
        mqtt.DOMAIN: {
            button.DOMAIN: {
                "name": "test",
                "command_topic": "command-topic",
                "payload_press": 1,
            }
        }
    }
    await help_test_default_availability_payload(
        menuai, mqtt_mock_entry, button.DOMAIN, config, True, "state-topic", "1"
    )


async def test_custom_availability_payload(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test availability by custom payload with defined topic."""
    config = {
        mqtt.DOMAIN: {
            button.DOMAIN: {
                "name": "test",
                "command_topic": "command-topic",
                "payload_press": 1,
            }
        }
    }

    await help_test_custom_availability_payload(
        menuai, mqtt_mock_entry, button.DOMAIN, config, True, "state-topic", "1"
    )


async def test_setting_attribute_via_mqtt_json_message(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the setting of attribute via MQTT with JSON payload."""
    await help_test_setting_attribute_via_mqtt_json_message(
        menuai, mqtt_mock_entry, button.DOMAIN, DEFAULT_CONFIG
    )


async def test_setting_blocked_attribute_via_mqtt_json_message(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the setting of attribute via MQTT with JSON payload."""
    await help_test_setting_blocked_attribute_via_mqtt_json_message(
        menuai, mqtt_mock_entry, button.DOMAIN, DEFAULT_CONFIG, None
    )


async def test_setting_attribute_with_template(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the setting of attribute via MQTT with JSON payload."""
    await help_test_setting_attribute_with_template(
        menuai, mqtt_mock_entry, button.DOMAIN, DEFAULT_CONFIG
    )


async def test_update_with_json_attrs_not_dict(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test attributes get extracted from a JSON result."""
    await help_test_update_with_json_attrs_not_dict(
        menuai, mqtt_mock_entry, caplog, button.DOMAIN, DEFAULT_CONFIG
    )


async def test_update_with_json_attrs_bad_json(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test attributes get extracted from a JSON result."""
    await help_test_update_with_json_attrs_bad_json(
        menuai, mqtt_mock_entry, caplog, button.DOMAIN, DEFAULT_CONFIG
    )


async def test_discovery_update_attr(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test update of discovered MQTTAttributes."""
    await help_test_discovery_update_attr(
        menuai, mqtt_mock_entry, button.DOMAIN, DEFAULT_CONFIG
    )


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                button.DOMAIN: [
                    {
                        "name": "Test 1",
                        "command_topic": "command-topic",
                        "unique_id": "TOTALLY_UNIQUE",
                    },
                    {
                        "name": "Test 2",
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
    """Test unique id option only creates one button per unique_id."""
    await help_test_unique_id(menuai, mqtt_mock_entry, button.DOMAIN)


async def test_discovery_removal_button(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test removal of discovered button."""
    data = '{ "name": "test", "command_topic": "test_topic" }'
    await help_test_discovery_removal(menuai, mqtt_mock_entry, button.DOMAIN, data)


async def test_discovery_update_button(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test update of discovered button."""
    config1 = copy.deepcopy(DEFAULT_CONFIG[mqtt.DOMAIN][button.DOMAIN])
    config2 = copy.deepcopy(DEFAULT_CONFIG[mqtt.DOMAIN][button.DOMAIN])
    config1["name"] = "Beer"
    config2["name"] = "Milk"

    await help_test_discovery_update(
        menuai, mqtt_mock_entry, button.DOMAIN, config1, config2
    )


async def test_discovery_update_unchanged_button(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test update of discovered button."""
    data1 = (
        '{ "name": "Beer",'
        '  "state_topic": "test_topic",'
        '  "command_topic": "test_topic" }'
    )
    with patch(
        "menuai.components.mqtt.button.MqttButton.discovery_update"
    ) as discovery_update:
        await help_test_discovery_update_unchanged(
            menuai, mqtt_mock_entry, button.DOMAIN, data1, discovery_update
        )


@pytest.mark.no_fail_on_log_exception
async def test_discovery_broken(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test handling of bad discovery message."""
    data1 = '{ "name": "Beer" }'
    data2 = '{ "name": "Milk", "command_topic": "test_topic" }'
    await help_test_discovery_broken(menuai, mqtt_mock_entry, button.DOMAIN, data1, data2)


async def test_entity_device_info_with_connection(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT button device registry integration."""
    await help_test_entity_device_info_with_connection(
        menuai, mqtt_mock_entry, button.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_device_info_with_identifier(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT button device registry integration."""
    await help_test_entity_device_info_with_identifier(
        menuai, mqtt_mock_entry, button.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_device_info_update(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test device registry update."""
    await help_test_entity_device_info_update(
        menuai, mqtt_mock_entry, button.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_device_info_remove(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test device registry remove."""
    await help_test_entity_device_info_remove(
        menuai, mqtt_mock_entry, button.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_id_update_discovery_update(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT discovery update when entity_id is updated."""
    await help_test_entity_id_update_discovery_update(
        menuai, mqtt_mock_entry, button.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_debug_info_message(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT debug info."""
    await help_test_entity_debug_info_message(
        menuai,
        mqtt_mock_entry,
        button.DOMAIN,
        DEFAULT_CONFIG,
        button.SERVICE_PRESS,
        command_payload="PRESS",
        state_topic=None,
    )


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                button.DOMAIN: {
                    "name": "test",
                    "command_topic": "test-topic",
                    "device_class": "foobarnotreal",
                }
            }
        }
    ],
)
async def test_invalid_device_class(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test device_class option with invalid value."""
    assert await mqtt_mock_entry()
    assert "expected ButtonDeviceClass" in caplog.text


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                button.DOMAIN: [
                    {
                        "name": "Test 1",
                        "command_topic": "test-topic",
                        "device_class": "update",
                    },
                    {
                        "name": "Test 2",
                        "command_topic": "test-topic",
                        "device_class": "restart",
                    },
                    {
                        "name": "Test 3",
                        "command_topic": "test-topic",
                    },
                    {
                        "name": "Test 4",
                        "command_topic": "test-topic",
                        "device_class": None,
                    },
                ]
            }
        }
    ],
)
async def test_valid_device_class(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test device_class option with valid values."""
    await mqtt_mock_entry()

    state = menuai.states.get("button.test_1")
    assert state.attributes["device_class"] == button.ButtonDeviceClass.UPDATE
    state = menuai.states.get("button.test_2")
    assert state.attributes["device_class"] == button.ButtonDeviceClass.RESTART
    state = menuai.states.get("button.test_3")
    assert "device_class" not in state.attributes


@pytest.mark.parametrize(
    ("service", "topic", "parameters", "payload", "template"),
    [
        (button.SERVICE_PRESS, "command_topic", None, "PRESS", "command_template"),
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
    domain = button.DOMAIN
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
    domain = button.DOMAIN
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
    platform = button.DOMAIN
    assert menuai.states.get(f"{platform}.test")


async def test_unload_entry(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test unloading the config entry."""
    domain = button.DOMAIN
    config = DEFAULT_CONFIG
    await help_test_unload_config_entry_with_platform(
        menuai, mqtt_mock_entry, domain, config
    )


@pytest.mark.parametrize(
    ("expected_friendly_name", "device_class"),
    [
        ("test", None),
        ("Update", "update"),
        ("Identify", "identify"),
        ("Restart", "restart"),
    ],
)
async def test_entity_name(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    expected_friendly_name: str | None,
    device_class: str | None,
) -> None:
    """Test the entity name setup."""
    domain = button.DOMAIN
    config = DEFAULT_CONFIG
    await help_test_entity_name(
        menuai, mqtt_mock_entry, domain, config, expected_friendly_name, device_class
    )


async def test_entity_icon_and_entity_picture(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
) -> None:
    """Test the entity icon or picture setup."""
    domain = button.DOMAIN
    config = DEFAULT_CONFIG
    await help_test_entity_icon_and_entity_picture(
        menuai, mqtt_mock_entry, domain, config
    )
