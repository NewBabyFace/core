"""The tests for the  MQTT binary sensor platform."""

import copy
from datetime import datetime, timedelta
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

from freezegun import freeze_time
from freezegun.api import FrozenDateTimeFactory
import pytest

from menuai.components import binary_sensor, mqtt
from menuai.const import (
    EVENT_STATE_CHANGED,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from menuai.core import menuai, State, callback
from menuai.helpers.typing import ConfigType
from menuai.util import dt as dt_util

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
    help_test_entity_icon_and_entity_picture,
    help_test_entity_id_update_discovery_update,
    help_test_entity_id_update_subscriptions,
    help_test_entity_name,
    help_test_reload_with_config,
    help_test_reloadable,
    help_test_setting_attribute_via_mqtt_json_message,
    help_test_setting_attribute_with_template,
    help_test_skipped_async_ha_write_state,
    help_test_unique_id,
    help_test_unload_config_entry_with_platform,
    help_test_update_with_json_attrs_bad_json,
    help_test_update_with_json_attrs_not_dict,
)

from tests.common import (
    async_fire_mqtt_message,
    async_fire_time_changed,
    mock_restore_cache,
)
from tests.typing import MqttMockHAClientGenerator, MqttMockPahoClient

DEFAULT_CONFIG = {
    mqtt.DOMAIN: {
        binary_sensor.DOMAIN: {
            "name": "test",
            "state_topic": "test-topic",
        }
    }
}


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                binary_sensor.DOMAIN: {
                    "name": "test",
                    "state_topic": "test-topic",
                    "expire_after": 4,
                    "force_update": True,
                    "availability_topic": "availability-topic",
                }
            }
        }
    ],
)
async def test_setting_sensor_value_expires_availability_topic(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
) -> None:
    """Test the expiration of the value."""
    await mqtt_mock_entry()

    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_UNAVAILABLE

    async_fire_mqtt_message(menuai, "availability-topic", "online")

    # State should be unavailable since expire_after is defined and > 0
    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_UNAVAILABLE

    await expires_helper(menuai)


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                binary_sensor.DOMAIN: {
                    "name": "test",
                    "state_topic": "test-topic",
                    "expire_after": 4,
                }
            }
        }
    ],
)
async def test_setting_sensor_value_expires(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the expiration of the value."""
    await mqtt_mock_entry()

    # State should be unavailable since expire_after is defined and > 0
    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_UNAVAILABLE

    await expires_helper(menuai)


async def expires_helper(menuai: menuai) -> None:
    """Run the basic expiry code."""
    realnow = dt_util.utcnow()
    now = datetime(realnow.year + 1, 1, 1, 1, tzinfo=dt_util.UTC)
    with freeze_time(now) as freezer:
        freezer.move_to(now)
        async_fire_time_changed(menuai, now)
        async_fire_mqtt_message(menuai, "test-topic", "ON")
        await menuai.async_block_till_done()

        # Value was set correctly.
        state = menuai.states.get("binary_sensor.test")
        assert state.state == STATE_ON

        # Time jump +3s
        now += timedelta(seconds=3)
        freezer.move_to(now)
        async_fire_time_changed(menuai, now)
        await menuai.async_block_till_done()

        # Value is not yet expired
        state = menuai.states.get("binary_sensor.test")
        assert state.state == STATE_ON

        # Next message resets timer
        # Time jump 0.5s
        now += timedelta(seconds=0.5)
        freezer.move_to(now)
        async_fire_time_changed(menuai, now)
        async_fire_mqtt_message(menuai, "test-topic", "OFF")
        await menuai.async_block_till_done()

        # Value was updated correctly.
        state = menuai.states.get("binary_sensor.test")
        assert state.state == STATE_OFF

        # Time jump +3s
        now += timedelta(seconds=3)
        freezer.move_to(now)
        async_fire_time_changed(menuai, now)
        await menuai.async_block_till_done()

        # Value is not yet expired
        state = menuai.states.get("binary_sensor.test")
        assert state.state == STATE_OFF

        # Time jump +2s
        now += timedelta(seconds=2)
        freezer.move_to(now)
        async_fire_time_changed(menuai, now)
        await menuai.async_block_till_done()

        # Value is expired now
        state = menuai.states.get("binary_sensor.test")
        assert state.state == STATE_UNAVAILABLE

        # Send the last message again
        # Time jump 0.5s
        now += timedelta(seconds=0.5)
        freezer.move_to(now)
        async_fire_time_changed(menuai, now)
        async_fire_mqtt_message(menuai, "test-topic", "OFF")
        await menuai.async_block_till_done()

        # Value was updated correctly.
        state = menuai.states.get("binary_sensor.test")
        assert state.state == STATE_OFF


async def test_expiration_on_discovery_and_discovery_update_of_binary_sensor(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that binary_sensor with expire_after set behaves correctly on discovery and discovery update."""
    await mqtt_mock_entry()
    config = {
        "name": "Test",
        "state_topic": "test-topic",
        "expire_after": 4,
        "force_update": True,
    }

    config_msg = json.dumps(config)

    # Set time and publish config message to create binary_sensor via discovery with 4 s expiry
    realnow = dt_util.utcnow()
    now = datetime(realnow.year + 1, 1, 1, 1, tzinfo=dt_util.UTC)
    freezer.move_to(now)
    async_fire_time_changed(menuai, now)
    async_fire_mqtt_message(menuai, "menuai/binary_sensor/bla/config", config_msg)
    await menuai.async_block_till_done()

    # Test that binary_sensor is not available
    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_UNAVAILABLE

    # Publish state message
    async_fire_mqtt_message(menuai, "test-topic", "ON")
    await menuai.async_block_till_done()

    # Test that binary_sensor has correct state
    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_ON

    # Advance +3 seconds
    now += timedelta(seconds=3)
    freezer.move_to(now)
    async_fire_time_changed(menuai, now)
    await menuai.async_block_till_done()

    # binary_sensor is not yet expired
    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_ON

    # Resend config message to update discovery
    with patch(("menuai.helpers.event.dt_util.utcnow"), return_value=now):
        async_fire_time_changed(menuai, now)
        async_fire_mqtt_message(
            menuai, "menuai/binary_sensor/bla/config", config_msg
        )
        await menuai.async_block_till_done()

    # Test that binary_sensor has not expired
    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_ON

    # Add +2 seconds
    now += timedelta(seconds=2)
    freezer.move_to(now)
    async_fire_time_changed(menuai, now)
    await menuai.async_block_till_done()

    # Test that binary_sensor has expired
    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_UNAVAILABLE

    # Resend config message to update discovery
    async_fire_mqtt_message(menuai, "menuai/binary_sensor/bla/config", config_msg)
    await menuai.async_block_till_done()

    # Test that binary_sensor is still expired
    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_UNAVAILABLE


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                binary_sensor.DOMAIN: {
                    "name": "test",
                    "state_topic": "test-topic",
                    "payload_on": "ON",
                    "payload_off": "OFF",
                }
            }
        }
    ],
)
async def test_setting_sensor_value_via_mqtt_message(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the setting of the value via MQTT."""
    await mqtt_mock_entry()

    state = menuai.states.get("binary_sensor.test")

    assert state.state == STATE_UNKNOWN

    async_fire_mqtt_message(menuai, "test-topic", "ON")
    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_ON

    async_fire_mqtt_message(menuai, "test-topic", "OFF")
    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_OFF

    async_fire_mqtt_message(menuai, "test-topic", "None")
    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_UNKNOWN


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                binary_sensor.DOMAIN: {
                    "name": "test",
                    "state_topic": "test-topic",
                    "payload_on": "ON",
                    "payload_off": "OFF",
                }
            }
        }
    ],
)
async def test_invalid_sensor_value_via_mqtt_message(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the setting of the value via MQTT."""
    await mqtt_mock_entry()

    state = menuai.states.get("binary_sensor.test")

    assert state.state == STATE_UNKNOWN

    async_fire_mqtt_message(menuai, "test-topic", "0N")
    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_UNKNOWN
    assert "No matching payload found for entity" in caplog.text
    caplog.clear()
    assert "No matching payload found for entity" not in caplog.text

    async_fire_mqtt_message(menuai, "test-topic", "ON")
    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_ON

    async_fire_mqtt_message(menuai, "test-topic", "0FF")
    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_ON
    assert "No matching payload found for entity" in caplog.text


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                binary_sensor.DOMAIN: {
                    "name": "test",
                    "state_topic": "test-topic",
                    "payload_on": "ON",
                    "payload_off": "OFF",
                    "value_template": '{%if is_state(entity_id,"on")-%}OFF'
                    "{%-else-%}ON{%-endif%}",
                }
            }
        }
    ],
)
async def test_setting_sensor_value_via_mqtt_message_and_template(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the setting of the value via MQTT."""
    await mqtt_mock_entry()

    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_UNKNOWN

    async_fire_mqtt_message(menuai, "test-topic", "")
    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_ON

    async_fire_mqtt_message(menuai, "test-topic", "")
    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_OFF


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                binary_sensor.DOMAIN: {
                    "name": "test",
                    "state_topic": "test-topic",
                    "payload_on": "ON",
                    "payload_off": "OFF",
                    "value_template": "{{value | upper}}",
                }
            }
        },
    ],
)
async def test_setting_sensor_value_via_mqtt_message_and_template2(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the setting of the value via MQTT."""
    await mqtt_mock_entry()

    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_UNKNOWN

    async_fire_mqtt_message(menuai, "test-topic", "on")
    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_ON

    async_fire_mqtt_message(menuai, "test-topic", "off")
    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_OFF

    async_fire_mqtt_message(menuai, "test-topic", "illegal")
    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_OFF
    assert "template output: 'ILLEGAL'" in caplog.text


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                binary_sensor.DOMAIN: {
                    "name": "test",
                    "encoding": "",
                    "state_topic": "test-topic",
                    "payload_on": "ON",
                    "payload_off": "OFF",
                    "value_template": "{%if value|unpack('b')-%}ON{%else%}OFF{%-endif-%}",
                }
            }
        }
    ],
)
async def test_setting_sensor_value_via_mqtt_message_and_template_and_raw_state_encoding(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test processing a raw value via MQTT."""
    await mqtt_mock_entry()

    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_UNKNOWN

    async_fire_mqtt_message(menuai, "test-topic", b"\x01")
    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_ON

    async_fire_mqtt_message(menuai, "test-topic", b"\x00")
    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_OFF


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                binary_sensor.DOMAIN: {
                    "name": "test",
                    "state_topic": "test-topic",
                    "payload_on": "ON",
                    "payload_off": "OFF",
                    "value_template": '{%if value == "ABC"%}ON{%endif%}',
                }
            }
        }
    ],
)
async def test_setting_sensor_value_via_mqtt_message_empty_template(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the setting of the value via MQTT."""
    await mqtt_mock_entry()

    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_UNKNOWN

    async_fire_mqtt_message(menuai, "test-topic", "DEF")
    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_UNKNOWN

    async_fire_mqtt_message(menuai, "test-topic", "ABC")
    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_ON


@pytest.mark.parametrize(
    ("menuai_config", "device_class"),
    [
        (
            {
                mqtt.DOMAIN: {
                    binary_sensor.DOMAIN: {
                        "name": "test",
                        "device_class": "motion",
                        "state_topic": "test-topic",
                    }
                }
            },
            "motion",
        ),
        (
            {
                mqtt.DOMAIN: {
                    binary_sensor.DOMAIN: {
                        "name": "test",
                        "device_class": None,
                        "state_topic": "test-topic",
                    }
                }
            },
            None,
        ),
    ],
)
async def test_valid_device_class(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    device_class: str | None,
) -> None:
    """Test the setting of a valid sensor class and ignoring an empty device_class."""
    await mqtt_mock_entry()

    state = menuai.states.get("binary_sensor.test")
    assert state.attributes.get("device_class") == device_class


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                binary_sensor.DOMAIN: {
                    "name": "test",
                    "device_class": "abc123",
                    "state_topic": "test-topic",
                }
            }
        }
    ],
)
async def test_invalid_device_class(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    mqtt_mock_entry: MqttMockHAClientGenerator,
) -> None:
    """Test the setting of an invalid sensor class."""
    assert await mqtt_mock_entry()
    assert "expected BinarySensorDeviceClass" in caplog.text


@pytest.mark.parametrize("menuai_config", [DEFAULT_CONFIG])
async def test_availability_when_connection_lost(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test availability after MQTT disconnection."""
    await help_test_availability_when_connection_lost(
        menuai, mqtt_mock_entry, binary_sensor.DOMAIN
    )


@pytest.mark.parametrize("menuai_config", [DEFAULT_CONFIG])
async def test_availability_without_topic(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test availability without defined availability topic."""
    await help_test_availability_without_topic(
        menuai, mqtt_mock_entry, binary_sensor.DOMAIN, DEFAULT_CONFIG
    )


async def test_default_availability_payload(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test availability by default payload with defined topic."""
    await help_test_default_availability_payload(
        menuai, mqtt_mock_entry, binary_sensor.DOMAIN, DEFAULT_CONFIG
    )


async def test_custom_availability_payload(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test availability by custom payload with defined topic."""
    await help_test_custom_availability_payload(
        menuai, mqtt_mock_entry, binary_sensor.DOMAIN, DEFAULT_CONFIG
    )


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                binary_sensor.DOMAIN: {
                    "name": "test",
                    "state_topic": "test-topic",
                    "payload_on": "ON",
                    "payload_off": "OFF",
                }
            }
        }
    ],
)
async def test_force_update_disabled(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test force update option."""
    await mqtt_mock_entry()

    events = []

    @callback
    def test_callback(event) -> None:
        """Verify event got called."""
        events.append(event)

    menuai.bus.async_listen(EVENT_STATE_CHANGED, test_callback)

    async_fire_mqtt_message(menuai, "test-topic", "ON")
    await menuai.async_block_till_done()
    assert len(events) == 1

    async_fire_mqtt_message(menuai, "test-topic", "ON")
    await menuai.async_block_till_done()
    assert len(events) == 1


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                binary_sensor.DOMAIN: {
                    "name": "test",
                    "state_topic": "test-topic",
                    "payload_on": "ON",
                    "payload_off": "OFF",
                    "force_update": True,
                }
            }
        }
    ],
)
async def test_force_update_enabled(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test force update option."""
    await mqtt_mock_entry()

    events = []

    @callback
    def test_callback(event) -> None:
        """Verify event got called."""
        events.append(event)

    menuai.bus.async_listen(EVENT_STATE_CHANGED, test_callback)

    async_fire_mqtt_message(menuai, "test-topic", "ON")
    await menuai.async_block_till_done()
    assert len(events) == 1

    async_fire_mqtt_message(menuai, "test-topic", "ON")
    await menuai.async_block_till_done()
    assert len(events) == 2


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                binary_sensor.DOMAIN: {
                    "name": "test",
                    "state_topic": "test-topic",
                    "payload_on": "ON",
                    "payload_off": "OFF",
                    "off_delay": 30,
                    "force_update": True,
                }
            }
        }
    ],
)
async def test_off_delay(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test off_delay option."""
    await mqtt_mock_entry()

    events = []

    @callback
    def test_callback(event) -> None:
        """Verify event got called."""
        events.append(event)

    menuai.bus.async_listen(EVENT_STATE_CHANGED, test_callback)

    async_fire_mqtt_message(menuai, "test-topic", "ON")
    await menuai.async_block_till_done()
    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_ON
    assert len(events) == 1

    async_fire_mqtt_message(menuai, "test-topic", "ON")
    await menuai.async_block_till_done()
    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_ON
    assert len(events) == 2

    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=30))
    await menuai.async_block_till_done()
    state = menuai.states.get("binary_sensor.test")
    assert state.state == STATE_OFF
    assert len(events) == 3


async def test_setting_attribute_via_mqtt_json_message(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the setting of attribute via MQTT with JSON payload."""
    await help_test_setting_attribute_via_mqtt_json_message(
        menuai, mqtt_mock_entry, binary_sensor.DOMAIN, DEFAULT_CONFIG
    )


async def test_setting_attribute_with_template(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the setting of attribute via MQTT with JSON payload."""
    await help_test_setting_attribute_with_template(
        menuai, mqtt_mock_entry, binary_sensor.DOMAIN, DEFAULT_CONFIG
    )


async def test_update_with_json_attrs_not_dict(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test attributes get extracted from a JSON result."""
    await help_test_update_with_json_attrs_not_dict(
        menuai, mqtt_mock_entry, caplog, binary_sensor.DOMAIN, DEFAULT_CONFIG
    )


async def test_update_with_json_attrs_bad_json(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test attributes get extracted from a JSON result."""
    await help_test_update_with_json_attrs_bad_json(
        menuai, mqtt_mock_entry, caplog, binary_sensor.DOMAIN, DEFAULT_CONFIG
    )


async def test_discovery_update_attr(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test update of discovered MQTTAttributes."""
    await help_test_discovery_update_attr(
        menuai, mqtt_mock_entry, binary_sensor.DOMAIN, DEFAULT_CONFIG
    )


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                binary_sensor.DOMAIN: [
                    {
                        "name": "Test 1",
                        "state_topic": "test-topic",
                        "unique_id": "TOTALLY_UNIQUE",
                    },
                    {
                        "name": "Test 2",
                        "state_topic": "test-topic",
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
    """Test unique id option only creates one sensor per unique_id."""
    await help_test_unique_id(menuai, mqtt_mock_entry, binary_sensor.DOMAIN)


async def test_discovery_removal_binary_sensor(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test removal of discovered binary_sensor."""
    data = json.dumps(DEFAULT_CONFIG[mqtt.DOMAIN][binary_sensor.DOMAIN])
    await help_test_discovery_removal(menuai, mqtt_mock_entry, binary_sensor.DOMAIN, data)


async def test_discovery_update_binary_sensor_topic_template(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test update of discovered binary_sensor."""
    config1 = copy.deepcopy(DEFAULT_CONFIG[mqtt.DOMAIN][binary_sensor.DOMAIN])
    config2 = copy.deepcopy(DEFAULT_CONFIG[mqtt.DOMAIN][binary_sensor.DOMAIN])
    config1["name"] = "Beer"
    config2["name"] = "Milk"
    config1["state_topic"] = "sensor/state1"
    config2["state_topic"] = "sensor/state2"
    config1["value_template"] = "{{ value_json.state1.state }}"
    config2["value_template"] = "{{ value_json.state2.state }}"

    state_data1 = [
        ([("sensor/state1", '{"state1":{"state":"ON"}}')], "on", None),
    ]
    state_data2 = [
        ([("sensor/state2", '{"state2":{"state":"OFF"}}')], "off", None),
        ([("sensor/state2", '{"state2":{"state":"ON"}}')], "on", None),
        ([("sensor/state1", '{"state1":{"state":"OFF"}}')], "on", None),
        ([("sensor/state1", '{"state2":{"state":"OFF"}}')], "on", None),
        ([("sensor/state2", '{"state1":{"state":"OFF"}}')], "on", None),
        ([("sensor/state2", '{"state2":{"state":"OFF"}}')], "off", None),
    ]

    await help_test_discovery_update(
        menuai,
        mqtt_mock_entry,
        binary_sensor.DOMAIN,
        config1,
        config2,
        state_data1=state_data1,
        state_data2=state_data2,
    )


async def test_discovery_update_binary_sensor_template(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test update of discovered binary_sensor."""
    config1 = copy.deepcopy(DEFAULT_CONFIG[mqtt.DOMAIN][binary_sensor.DOMAIN])
    config2 = copy.deepcopy(DEFAULT_CONFIG[mqtt.DOMAIN][binary_sensor.DOMAIN])
    config1["name"] = "Beer"
    config2["name"] = "Milk"
    config1["state_topic"] = "sensor/state1"
    config2["state_topic"] = "sensor/state1"
    config1["value_template"] = "{{ value_json.state1.state }}"
    config2["value_template"] = "{{ value_json.state2.state }}"

    state_data1 = [
        ([("sensor/state1", '{"state1":{"state":"ON"}}')], "on", None),
    ]
    state_data2 = [
        ([("sensor/state1", '{"state2":{"state":"OFF"}}')], "off", None),
        ([("sensor/state1", '{"state2":{"state":"ON"}}')], "on", None),
        ([("sensor/state1", '{"state1":{"state":"OFF"}}')], "on", None),
        ([("sensor/state1", '{"state2":{"state":"OFF"}}')], "off", None),
    ]

    await help_test_discovery_update(
        menuai,
        mqtt_mock_entry,
        binary_sensor.DOMAIN,
        config1,
        config2,
        state_data1=state_data1,
        state_data2=state_data2,
    )


@pytest.mark.parametrize(
    ("topic", "value", "attribute", "attribute_value"),
    [
        ("json_attributes_topic", '{ "id": 123 }', "id", 123),
        (
            "json_attributes_topic",
            '{ "id": 123, "temperature": 34.0 }',
            "temperature",
            34.0,
        ),
        ("state_topic", "ON", None, "on"),
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
        binary_sensor.DOMAIN,
        DEFAULT_CONFIG[mqtt.DOMAIN][binary_sensor.DOMAIN],
        topic,
        value,
        attribute,
        attribute_value,
    )


async def test_discovery_update_unchanged_binary_sensor(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test update of discovered binary_sensor."""
    config1 = copy.deepcopy(DEFAULT_CONFIG[mqtt.DOMAIN][binary_sensor.DOMAIN])
    config1["name"] = "Beer"

    data1 = json.dumps(config1)
    with patch(
        "menuai.components.mqtt.binary_sensor.MqttBinarySensor.discovery_update"
    ) as discovery_update:
        await help_test_discovery_update_unchanged(
            menuai, mqtt_mock_entry, binary_sensor.DOMAIN, data1, discovery_update
        )


@pytest.mark.no_fail_on_log_exception
async def test_discovery_broken(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test handling of bad discovery message."""
    data1 = '{ "name": "Beer",  "off_delay": -1 }'
    data2 = '{ "name": "Milk",  "state_topic": "test_topic" }'
    await help_test_discovery_broken(
        menuai, mqtt_mock_entry, binary_sensor.DOMAIN, data1, data2
    )


async def test_entity_device_info_with_connection(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT binary sensor device registry integration."""
    await help_test_entity_device_info_with_connection(
        menuai, mqtt_mock_entry, binary_sensor.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_device_info_with_identifier(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT binary sensor device registry integration."""
    await help_test_entity_device_info_with_identifier(
        menuai, mqtt_mock_entry, binary_sensor.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_device_info_update(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test device registry update."""
    await help_test_entity_device_info_update(
        menuai, mqtt_mock_entry, binary_sensor.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_device_info_remove(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test device registry remove."""
    await help_test_entity_device_info_remove(
        menuai, mqtt_mock_entry, binary_sensor.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_id_update_subscriptions(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT subscriptions are managed when entity_id is updated."""
    await help_test_entity_id_update_subscriptions(
        menuai, mqtt_mock_entry, binary_sensor.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_id_update_discovery_update(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT discovery update when entity_id is updated."""
    await help_test_entity_id_update_discovery_update(
        menuai, mqtt_mock_entry, binary_sensor.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_debug_info_message(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT debug info."""
    await help_test_entity_debug_info_message(
        menuai, mqtt_mock_entry, binary_sensor.DOMAIN, DEFAULT_CONFIG, None
    )


async def test_reloadable(
    menuai: menuai, mqtt_client_mock: MqttMockPahoClient
) -> None:
    """Test reloading the MQTT platform."""
    domain = binary_sensor.DOMAIN
    config = DEFAULT_CONFIG
    await help_test_reloadable(menuai, mqtt_client_mock, domain, config)


@pytest.mark.usefixtures("mock_temp_dir")
@pytest.mark.parametrize(
    ("menuai_config", "payload1", "state1", "payload2", "state2"),
    [
        (
            help_custom_config(
                binary_sensor.DOMAIN,
                DEFAULT_CONFIG,
                (
                    {"name": "test1", "expire_after": 30, "state_topic": "test-topic1"},
                    {"name": "test2", "expire_after": 5, "state_topic": "test-topic2"},
                ),
            ),
            "ON",
            "on",
            "OFF",
            "off",
        ),
        (
            help_custom_config(
                binary_sensor.DOMAIN,
                DEFAULT_CONFIG,
                (
                    {"name": "test1", "expire_after": 30, "state_topic": "test-topic1"},
                    {"name": "test2", "expire_after": 5, "state_topic": "test-topic2"},
                ),
            ),
            "OFF",
            "off",
            "ON",
            "on",
        ),
    ],
)
async def test_cleanup_triggers_and_restoring_state(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
    freezer: FrozenDateTimeFactory,
    menuai_config: ConfigType,
    payload1: str,
    state1: str,
    payload2: str,
    state2: str,
) -> None:
    """Test cleanup old triggers at reloading and restoring the state."""
    freezer.move_to("2022-02-02 12:01:00+01:00")

    await mqtt_mock_entry()

    async_fire_mqtt_message(menuai, "test-topic1", payload1)
    state = menuai.states.get("binary_sensor.test1")
    assert state.state == state1

    async_fire_mqtt_message(menuai, "test-topic2", payload1)
    state = menuai.states.get("binary_sensor.test2")
    assert state.state == state1

    freezer.move_to("2022-02-02 12:01:10+01:00")

    await help_test_reload_with_config(
        menuai, caplog, tmp_path, {mqtt.DOMAIN: menuai_config}
    )

    state = menuai.states.get("binary_sensor.test1")
    assert state.state == state1

    state = menuai.states.get("binary_sensor.test2")
    assert state.state == STATE_UNAVAILABLE

    async_fire_mqtt_message(menuai, "test-topic1", payload2)
    state = menuai.states.get("binary_sensor.test1")
    assert state.state == state2

    async_fire_mqtt_message(menuai, "test-topic2", payload2)
    state = menuai.states.get("binary_sensor.test2")
    assert state.state == state2

    await menuai.async_block_till_done(wait_background_tasks=True)


@pytest.mark.parametrize(
    "menuai_config",
    [
        help_custom_config(
            binary_sensor.DOMAIN,
            DEFAULT_CONFIG,
            ({"name": "test3", "expire_after": 10, "state_topic": "test-topic3"},),
        )
    ],
)
async def test_skip_restoring_state_with_over_due_expire_trigger(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test restoring a state with over due expire timer."""

    freezer.move_to("2022-02-02 12:02:00+01:00")
    domain = binary_sensor.DOMAIN
    config3: ConfigType = copy.deepcopy(DEFAULT_CONFIG[mqtt.DOMAIN][domain])
    config3["name"] = "test3"
    config3["expire_after"] = 10
    config3["state_topic"] = "test-topic3"
    fake_state = State(
        "binary_sensor.test3",
        "on",
        {},
        last_changed=datetime.fromisoformat("2022-02-02 12:01:35+01:00"),
    )
    mock_restore_cache(menuai, (fake_state,))

    await mqtt_mock_entry()
    state = menuai.states.get("binary_sensor.test3")
    assert state.state == STATE_UNAVAILABLE


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
    platform = binary_sensor.DOMAIN
    assert menuai.states.get(f"{platform}.test")


async def test_unload_entry(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test unloading the config entry."""
    domain = binary_sensor.DOMAIN
    config = DEFAULT_CONFIG
    await help_test_unload_config_entry_with_platform(
        menuai, mqtt_mock_entry, domain, config
    )


@pytest.mark.parametrize(
    ("expected_friendly_name", "device_class"),
    [("test", None), ("Door", "door"), ("Battery", "battery"), ("Motion", "motion")],
)
async def test_entity_name(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    expected_friendly_name: str | None,
    device_class: str | None,
) -> None:
    """Test the entity name setup."""
    domain = binary_sensor.DOMAIN
    config = DEFAULT_CONFIG
    await help_test_entity_name(
        menuai, mqtt_mock_entry, domain, config, expected_friendly_name, device_class
    )


async def test_entity_icon_and_entity_picture(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
) -> None:
    """Test the entity icon or picture setup."""
    domain = binary_sensor.DOMAIN
    config = DEFAULT_CONFIG
    await help_test_entity_icon_and_entity_picture(
        menuai, mqtt_mock_entry, domain, config
    )


@pytest.mark.parametrize(
    "menuai_config",
    [
        help_custom_config(
            binary_sensor.DOMAIN,
            DEFAULT_CONFIG,
            (
                {
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
        ("test-topic", "ON", "OFF"),
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
            binary_sensor.DOMAIN,
            DEFAULT_CONFIG,
            (
                {
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
