"""The tests for mqtt select component."""

from collections.abc import Generator
import copy
import json
import logging
from typing import Any
from unittest.mock import patch

import pytest

from menuai.components import mqtt, select
from menuai.components.mqtt.select import MQTT_SELECT_ATTRIBUTES_BLOCKED
from menuai.components.select import (
    ATTR_OPTION,
    ATTR_OPTIONS,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from menuai.const import ATTR_ASSUMED_STATE, ATTR_ENTITY_ID, STATE_UNKNOWN
from menuai.core import menuai, State
from menuai.helpers.typing import ConfigType

from .common import (
    help_custom_config,
    help_test_availability_when_connection_lost,
    help_test_availability_without_topic,
    help_test_custom_availability_payload,
    help_test_default_availability_payload,
    help_test_discovery_broken,
    help_test_discovery_removal,
    help_test_discovery_setup,
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

from tests.common import async_fire_mqtt_message, mock_restore_cache
from tests.typing import MqttMockHAClientGenerator, MqttMockPahoClient

DEFAULT_CONFIG = {
    mqtt.DOMAIN: {
        select.DOMAIN: {
            "name": "test",
            "command_topic": "test-topic",
            "options": ["milk", "beer"],
        }
    }
}


def _test_run_select_setup_params(topic: str) -> Generator[tuple[ConfigType, str]]:
    yield (
        {
            mqtt.DOMAIN: {
                select.DOMAIN: {
                    "state_topic": topic,
                    "command_topic": "test/select_cmd",
                    "name": "Test Select",
                    "options": ["milk", "beer"],
                }
            }
        },
        topic,
    )


@pytest.mark.parametrize(
    ("menuai_config", "topic"),
    _test_run_select_setup_params("test/select_stat"),
)
async def test_run_select_setup(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
    topic: str,
) -> None:
    """Test that it fetches the given payload."""
    await mqtt_mock_entry()

    state = menuai.states.get("select.test_select")
    assert state.state == STATE_UNKNOWN

    async_fire_mqtt_message(menuai, topic, "milk")

    await menuai.async_block_till_done()

    state = menuai.states.get("select.test_select")
    assert state.state == "milk"

    async_fire_mqtt_message(menuai, topic, "beer")

    await menuai.async_block_till_done()

    state = menuai.states.get("select.test_select")
    assert state.state == "beer"

    if caplog.at_level(logging.DEBUG):
        async_fire_mqtt_message(menuai, topic, "")
        await menuai.async_block_till_done()

        assert "Ignoring empty payload" in caplog.text

    state = menuai.states.get("select.test_select")
    assert state.state == "beer"


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                select.DOMAIN: {
                    "state_topic": "test/select_stat",
                    "command_topic": "test/select_cmd",
                    "name": "Test Select",
                    "options": ["milk", "beer"],
                    "value_template": "{{ value_json.val }}",
                }
            }
        }
    ],
)
async def test_value_template(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test that it fetches the given payload with a template."""
    await mqtt_mock_entry()

    async_fire_mqtt_message(menuai, "test/select_stat", '{"val":"milk"}')

    await menuai.async_block_till_done()

    state = menuai.states.get("select.test_select")
    assert state.state == "milk"

    async_fire_mqtt_message(menuai, "test/select_stat", '{"val":"beer"}')

    await menuai.async_block_till_done()

    state = menuai.states.get("select.test_select")
    assert state.state == "beer"

    async_fire_mqtt_message(menuai, "test/select_stat", '{"val": null}')

    await menuai.async_block_till_done()

    state = menuai.states.get("select.test_select")
    assert state.state == STATE_UNKNOWN


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                select.DOMAIN: {
                    "command_topic": "test/select_cmd",
                    "name": "Test Select",
                    "options": ["milk", "beer"],
                }
            }
        }
    ],
)
async def test_run_select_service_optimistic(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test that set_value service works in optimistic mode."""
    fake_state = State("select.test_select", "milk")
    mock_restore_cache(menuai, (fake_state,))

    mqtt_mock = await mqtt_mock_entry()

    state = menuai.states.get("select.test_select")
    assert state.state == "milk"
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await menuai.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: "select.test_select", ATTR_OPTION: "beer"},
        blocking=True,
    )

    mqtt_mock.async_publish.assert_called_once_with("test/select_cmd", "beer", 0, False)
    mqtt_mock.async_publish.reset_mock()
    state = menuai.states.get("select.test_select")
    assert state.state == "beer"


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                select.DOMAIN: {
                    "command_topic": "test/select_cmd",
                    "name": "Test Select",
                    "options": ["milk", "beer"],
                    "command_template": '{"option": "{{ value }}"}',
                }
            }
        }
    ],
)
async def test_run_select_service_optimistic_with_command_template(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test that set_value service works in optimistic mode and with a command_template."""
    fake_state = State("select.test_select", "milk")
    mock_restore_cache(menuai, (fake_state,))

    mqtt_mock = await mqtt_mock_entry()

    state = menuai.states.get("select.test_select")
    assert state.state == "milk"
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await menuai.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: "select.test_select", ATTR_OPTION: "beer"},
        blocking=True,
    )

    mqtt_mock.async_publish.assert_called_once_with(
        "test/select_cmd", '{"option": "beer"}', 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = menuai.states.get("select.test_select")
    assert state.state == "beer"


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                select.DOMAIN: {
                    "command_topic": "test/select/set",
                    "state_topic": "test/select",
                    "name": "Test Select",
                    "options": ["milk", "beer"],
                }
            }
        }
    ],
)
async def test_run_select_service(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test that set_value service works in non optimistic mode."""
    cmd_topic = "test/select/set"
    state_topic = "test/select"

    mqtt_mock = await mqtt_mock_entry()

    async_fire_mqtt_message(menuai, state_topic, "beer")
    state = menuai.states.get("select.test_select")
    assert state.state == "beer"

    await menuai.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: "select.test_select", ATTR_OPTION: "milk"},
        blocking=True,
    )
    mqtt_mock.async_publish.assert_called_once_with(cmd_topic, "milk", 0, False)
    state = menuai.states.get("select.test_select")
    assert state.state == "beer"


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                select.DOMAIN: {
                    "command_topic": "test/select/set",
                    "state_topic": "test/select",
                    "name": "Test Select",
                    "options": ["milk", "beer"],
                    "command_template": '{"option": "{{ value }}"}',
                }
            }
        }
    ],
)
async def test_run_select_service_with_command_template(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test that set_value service works in non optimistic mode and with a command_template."""
    cmd_topic = "test/select/set"
    state_topic = "test/select"

    mqtt_mock = await mqtt_mock_entry()

    async_fire_mqtt_message(menuai, state_topic, "beer")
    state = menuai.states.get("select.test_select")
    assert state.state == "beer"

    await menuai.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: "select.test_select", ATTR_OPTION: "milk"},
        blocking=True,
    )
    mqtt_mock.async_publish.assert_called_once_with(
        cmd_topic, '{"option": "milk"}', 0, False
    )


@pytest.mark.parametrize("menuai_config", [DEFAULT_CONFIG])
async def test_availability_when_connection_lost(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test availability after MQTT disconnection."""
    await help_test_availability_when_connection_lost(
        menuai, mqtt_mock_entry, select.DOMAIN
    )


@pytest.mark.parametrize("menuai_config", [DEFAULT_CONFIG])
async def test_availability_without_topic(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test availability without defined availability topic."""
    await help_test_availability_without_topic(
        menuai, mqtt_mock_entry, select.DOMAIN, DEFAULT_CONFIG
    )


async def test_default_availability_payload(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test availability by default payload with defined topic."""
    await help_test_default_availability_payload(
        menuai, mqtt_mock_entry, select.DOMAIN, DEFAULT_CONFIG
    )


async def test_custom_availability_payload(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test availability by custom payload with defined topic."""
    await help_test_custom_availability_payload(
        menuai, mqtt_mock_entry, select.DOMAIN, DEFAULT_CONFIG
    )


async def test_setting_attribute_via_mqtt_json_message(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the setting of attribute via MQTT with JSON payload."""
    await help_test_setting_attribute_via_mqtt_json_message(
        menuai, mqtt_mock_entry, select.DOMAIN, DEFAULT_CONFIG
    )


async def test_setting_blocked_attribute_via_mqtt_json_message(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the setting of attribute via MQTT with JSON payload."""
    await help_test_setting_blocked_attribute_via_mqtt_json_message(
        menuai,
        mqtt_mock_entry,
        select.DOMAIN,
        DEFAULT_CONFIG,
        MQTT_SELECT_ATTRIBUTES_BLOCKED,
    )


async def test_setting_attribute_with_template(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the setting of attribute via MQTT with JSON payload."""
    await help_test_setting_attribute_with_template(
        menuai, mqtt_mock_entry, select.DOMAIN, DEFAULT_CONFIG
    )


async def test_update_with_json_attrs_not_dict(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test attributes get extracted from a JSON result."""
    await help_test_update_with_json_attrs_not_dict(
        menuai, mqtt_mock_entry, caplog, select.DOMAIN, DEFAULT_CONFIG
    )


async def test_update_with_json_attrs_bad_json(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test attributes get extracted from a JSON result."""
    await help_test_update_with_json_attrs_bad_json(
        menuai,
        mqtt_mock_entry,
        caplog,
        select.DOMAIN,
        DEFAULT_CONFIG,
    )


async def test_discovery_update_attr(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test update of discovered MQTTAttributes."""
    await help_test_discovery_update_attr(
        menuai, mqtt_mock_entry, select.DOMAIN, DEFAULT_CONFIG
    )


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                select.DOMAIN: [
                    {
                        "name": "Test 1",
                        "state_topic": "test-topic",
                        "command_topic": "test-topic",
                        "unique_id": "TOTALLY_UNIQUE",
                        "options": ["milk", "beer"],
                    },
                    {
                        "name": "Test 2",
                        "state_topic": "test-topic",
                        "command_topic": "test-topic",
                        "unique_id": "TOTALLY_UNIQUE",
                        "options": ["milk", "beer"],
                    },
                ]
            }
        }
    ],
)
async def test_unique_id(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test unique id option only creates one select per unique_id."""
    await help_test_unique_id(menuai, mqtt_mock_entry, select.DOMAIN)


async def test_discovery_removal_select(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test removal of discovered select."""
    data = json.dumps(DEFAULT_CONFIG[mqtt.DOMAIN][select.DOMAIN])
    await help_test_discovery_removal(menuai, mqtt_mock_entry, select.DOMAIN, data)


async def test_discovery_update_select(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test update of discovered select."""
    config1 = {
        "name": "Beer",
        "state_topic": "test-topic",
        "command_topic": "test-topic",
        "options": ["milk", "beer"],
    }
    config2 = {
        "name": "Milk",
        "state_topic": "test-topic",
        "command_topic": "test-topic",
        "options": ["milk"],
    }

    await help_test_discovery_update(
        menuai, mqtt_mock_entry, select.DOMAIN, config1, config2
    )


async def test_discovery_update_unchanged_select(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test update of discovered select."""
    data1 = '{ "name": "Beer", "state_topic": "test-topic", "command_topic": "test-topic", "options": ["milk", "beer"]}'
    with patch(
        "menuai.components.mqtt.select.MqttSelect.discovery_update"
    ) as discovery_update:
        await help_test_discovery_update_unchanged(
            menuai, mqtt_mock_entry, select.DOMAIN, data1, discovery_update
        )


@pytest.mark.no_fail_on_log_exception
async def test_discovery_broken(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test handling of bad discovery message."""
    data1 = '{ "name": "Beer" }'
    data2 = '{ "name": "Milk", "state_topic": "test-topic", "command_topic": "test-topic", "options": ["milk", "beer"]}'

    await help_test_discovery_broken(menuai, mqtt_mock_entry, select.DOMAIN, data1, data2)


async def test_entity_device_info_with_connection(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT select device registry integration."""
    await help_test_entity_device_info_with_connection(
        menuai, mqtt_mock_entry, select.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_device_info_with_identifier(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT select device registry integration."""
    await help_test_entity_device_info_with_identifier(
        menuai, mqtt_mock_entry, select.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_device_info_update(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test device registry update."""
    await help_test_entity_device_info_update(
        menuai, mqtt_mock_entry, select.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_device_info_remove(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test device registry remove."""
    await help_test_entity_device_info_remove(
        menuai, mqtt_mock_entry, select.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_id_update_subscriptions(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT subscriptions are managed when entity_id is updated."""
    await help_test_entity_id_update_subscriptions(
        menuai, mqtt_mock_entry, select.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_id_update_discovery_update(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT discovery update when entity_id is updated."""
    await help_test_entity_id_update_discovery_update(
        menuai, mqtt_mock_entry, select.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_debug_info_message(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT debug info."""
    await help_test_entity_debug_info_message(
        menuai,
        mqtt_mock_entry,
        select.DOMAIN,
        DEFAULT_CONFIG,
        select.SERVICE_SELECT_OPTION,
        service_parameters={ATTR_OPTION: "beer"},
        command_payload="beer",
        state_payload="milk",
    )


def _test_options_attributes_options_config(
    request: tuple[list[str]],
) -> Generator[tuple[ConfigType, list[str]]]:
    for option in request:
        yield (
            {
                mqtt.DOMAIN: {
                    select.DOMAIN: {
                        "command_topic": "test/select/set",
                        "state_topic": "test/select",
                        "name": "Test select",
                        "options": option,
                    }
                }
            },
            option,
        )


@pytest.mark.parametrize(
    ("menuai_config", "options"),
    _test_options_attributes_options_config((["milk", "beer"], ["milk"], [])),  # type:ignore[arg-type]
)
async def test_options_attributes(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator, options: list[str]
) -> None:
    """Test options attribute."""
    await mqtt_mock_entry()

    state = menuai.states.get("select.test_select")
    assert state.attributes.get(ATTR_OPTIONS) == options


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                select.DOMAIN: {
                    "state_topic": "test/select_stat",
                    "command_topic": "test/select_cmd",
                    "name": "Test Select",
                    "options": ["milk", "beer"],
                }
            }
        }
    ],
)
async def test_mqtt_payload_not_an_option_warning(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    mqtt_mock_entry: MqttMockHAClientGenerator,
) -> None:
    """Test warning for MQTT payload which is not a valid option."""
    await mqtt_mock_entry()

    async_fire_mqtt_message(menuai, "test/select_stat", "öl")

    await menuai.async_block_till_done()

    assert (
        "Invalid option for select.test_select: 'öl' (valid options: ['milk', 'beer'])"
        in caplog.text
    )


@pytest.mark.parametrize(
    ("service", "topic", "parameters", "payload", "template"),
    [
        (
            select.SERVICE_SELECT_OPTION,
            "command_topic",
            {"option": "beer"},
            "beer",
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
    domain = select.DOMAIN
    config = copy.deepcopy(DEFAULT_CONFIG)
    config[mqtt.DOMAIN][domain]["options"] = ["milk", "beer"]

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
    domain = select.DOMAIN
    config = DEFAULT_CONFIG
    await help_test_reloadable(menuai, mqtt_client_mock, domain, config)


@pytest.mark.parametrize(
    ("topic", "value", "attribute", "attribute_value"),
    [
        ("state_topic", "milk", None, "milk"),
        ("state_topic", "beer", None, "beer"),
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
    config = copy.deepcopy(DEFAULT_CONFIG[mqtt.DOMAIN][select.DOMAIN])
    config["options"] = ["milk", "beer"]
    await help_test_encoding_subscribable_topics(
        menuai,
        mqtt_mock_entry,
        select.DOMAIN,
        config,
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
    platform = select.DOMAIN
    assert menuai.states.get(f"{platform}.test")


async def test_unload_entry(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test unloading the config entry."""
    domain = select.DOMAIN
    config = DEFAULT_CONFIG
    await help_test_unload_config_entry_with_platform(
        menuai, mqtt_mock_entry, domain, config
    )


async def test_persistent_state_after_reconfig(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test of the state is persistent after reconfiguring the select options."""
    await mqtt_mock_entry()
    discovery_data = '{ "name": "Milk", "state_topic": "test-topic", "command_topic": "test-topic", "options": ["milk", "beer"]}'
    await help_test_discovery_setup(menuai, SELECT_DOMAIN, discovery_data, "milk")

    # assign an initial state
    async_fire_mqtt_message(menuai, "test-topic", "beer")
    state = menuai.states.get("select.milk")
    assert state.state == "beer"
    assert state.attributes["options"] == ["milk", "beer"]

    # remove "milk" option
    discovery_data = '{ "name": "Milk", "state_topic": "test-topic", "command_topic": "test-topic", "options": ["beer"]}'
    await help_test_discovery_setup(menuai, SELECT_DOMAIN, discovery_data, "milk")

    # assert the state persistent
    state = menuai.states.get("select.milk")
    assert state.state == "beer"
    assert state.attributes["options"] == ["beer"]


@pytest.mark.parametrize(
    "menuai_config",
    [
        help_custom_config(
            select.DOMAIN,
            DEFAULT_CONFIG,
            (
                {
                    "availability_topic": "availability-topic",
                    "json_attributes_topic": "json-attributes-topic",
                    "state_topic": "test-topic",
                },
            ),
        )
    ],
)
@pytest.mark.parametrize(
    ("topic", "payload1", "payload2"),
    [
        ("test-topic", "milk", "beer"),
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
            select.DOMAIN,
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
