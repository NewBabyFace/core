"""The tests for MQTT tag scanner."""

import copy
import json
from typing import Any
from unittest.mock import ANY, AsyncMock

import pytest

from menuai.components.device_automation import DeviceAutomationType
from menuai.components.mqtt.const import DOMAIN
from menuai.core import menuai
from menuai.helpers import device_registry as dr
from menuai.setup import async_setup_component

from .common import help_test_unload_config_entry

from tests.common import (
    MockConfigEntry,
    async_fire_mqtt_message,
    async_get_device_automations,
)
from tests.typing import MqttMockHAClientGenerator, WebSocketGenerator

DEFAULT_CONFIG_DEVICE = {
    "device": {"identifiers": ["0AFFD2"]},
    "topic": "foobar/tag_scanned",
}

DEFAULT_CONFIG = {
    "topic": "foobar/tag_scanned",
}

DEFAULT_CONFIG_JSON = {
    "device": {"identifiers": ["0AFFD2"]},
    "topic": "foobar/tag_scanned",
    "value_template": "{{ value_json.PN532.UID }}",
}

DEFAULT_TAG_ID = "E9F35959"

DEFAULT_TAG_SCAN = "E9F35959"

DEFAULT_TAG_SCAN_JSON = (
    '{"Time":"2020-09-28T17:02:10","PN532":{"UID":"E9F35959", "DATA":"ILOVETASMOTA"}}'
)


@pytest.mark.no_fail_on_log_exception
async def test_discover_bad_tag(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    tag_mock: AsyncMock,
) -> None:
    """Test bad discovery message."""
    await mqtt_mock_entry()
    config1 = copy.deepcopy(DEFAULT_CONFIG_DEVICE)

    # Test sending bad data
    data0 = '{ "device":{"identifiers":["0AFFD2"]}, "topics": "foobar/tag_scanned" }'
    async_fire_mqtt_message(menuai, "menuai/tag/bla/config", data0)
    await menuai.async_block_till_done()
    assert device_registry.async_get_device(identifiers={("mqtt", "0AFFD2")}) is None

    # Test sending correct data
    async_fire_mqtt_message(menuai, "menuai/tag/bla/config", json.dumps(config1))
    await menuai.async_block_till_done()

    device_entry = device_registry.async_get_device(identifiers={("mqtt", "0AFFD2")})
    # Fake tag scan.
    async_fire_mqtt_message(menuai, "foobar/tag_scanned", DEFAULT_TAG_SCAN)
    await menuai.async_block_till_done()
    tag_mock.assert_called_once_with(ANY, DEFAULT_TAG_ID, device_entry.id)


async def test_if_fires_on_mqtt_message_with_device(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    tag_mock: AsyncMock,
) -> None:
    """Test tag scanning, with device."""
    await mqtt_mock_entry()
    config = copy.deepcopy(DEFAULT_CONFIG_DEVICE)

    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", json.dumps(config))
    await menuai.async_block_till_done()
    device_entry = device_registry.async_get_device(identifiers={("mqtt", "0AFFD2")})

    # Fake tag scan.
    async_fire_mqtt_message(menuai, "foobar/tag_scanned", DEFAULT_TAG_SCAN)
    await menuai.async_block_till_done()
    tag_mock.assert_called_once_with(ANY, DEFAULT_TAG_ID, device_entry.id)


async def test_if_fires_on_mqtt_message_without_device(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator, tag_mock: AsyncMock
) -> None:
    """Test tag scanning, without device."""
    await mqtt_mock_entry()
    config = copy.deepcopy(DEFAULT_CONFIG)

    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", json.dumps(config))
    await menuai.async_block_till_done()

    # Fake tag scan.
    async_fire_mqtt_message(menuai, "foobar/tag_scanned", DEFAULT_TAG_SCAN)
    await menuai.async_block_till_done()
    tag_mock.assert_called_once_with(ANY, DEFAULT_TAG_ID, None)


async def test_if_fires_on_mqtt_message_with_template(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    tag_mock: AsyncMock,
) -> None:
    """Test tag scanning, with device."""
    await mqtt_mock_entry()
    config = copy.deepcopy(DEFAULT_CONFIG_JSON)

    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", json.dumps(config))
    await menuai.async_block_till_done()
    device_entry = device_registry.async_get_device(identifiers={("mqtt", "0AFFD2")})

    # Fake tag scan.
    async_fire_mqtt_message(menuai, "foobar/tag_scanned", DEFAULT_TAG_SCAN_JSON)
    await menuai.async_block_till_done()
    tag_mock.assert_called_once_with(ANY, DEFAULT_TAG_ID, device_entry.id)


async def test_strip_tag_id(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator, tag_mock: AsyncMock
) -> None:
    """Test strip whitespace from tag_id."""
    await mqtt_mock_entry()
    config = copy.deepcopy(DEFAULT_CONFIG)

    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", json.dumps(config))
    await menuai.async_block_till_done()

    # Fake tag scan.
    async_fire_mqtt_message(menuai, "foobar/tag_scanned", "123456   ")
    await menuai.async_block_till_done()
    tag_mock.assert_called_once_with(ANY, "123456", None)


async def test_if_fires_on_mqtt_message_after_update_with_device(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    tag_mock: AsyncMock,
) -> None:
    """Test tag scanning after update."""
    await mqtt_mock_entry()
    config1 = copy.deepcopy(DEFAULT_CONFIG_DEVICE)
    config1["some_future_option_1"] = "future_option_1"
    config2 = copy.deepcopy(DEFAULT_CONFIG_DEVICE)
    config2["some_future_option_2"] = "future_option_2"
    config2["topic"] = "foobar/tag_scanned2"

    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", json.dumps(config1))
    await menuai.async_block_till_done()
    device_entry = device_registry.async_get_device(identifiers={("mqtt", "0AFFD2")})

    # Fake tag scan.
    async_fire_mqtt_message(menuai, "foobar/tag_scanned", DEFAULT_TAG_SCAN)
    await menuai.async_block_till_done()
    tag_mock.assert_called_once_with(ANY, DEFAULT_TAG_ID, device_entry.id)

    # Update the tag scanner with different topic
    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", json.dumps(config2))
    await menuai.async_block_till_done()
    tag_mock.reset_mock()

    async_fire_mqtt_message(menuai, "foobar/tag_scanned", DEFAULT_TAG_SCAN)
    await menuai.async_block_till_done()
    tag_mock.assert_not_called()

    async_fire_mqtt_message(menuai, "foobar/tag_scanned2", DEFAULT_TAG_SCAN)
    await menuai.async_block_till_done()
    tag_mock.assert_called_once_with(ANY, DEFAULT_TAG_ID, device_entry.id)

    # Update the tag scanner with same topic
    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", json.dumps(config2))
    await menuai.async_block_till_done()
    tag_mock.reset_mock()

    async_fire_mqtt_message(menuai, "foobar/tag_scanned", DEFAULT_TAG_SCAN)
    await menuai.async_block_till_done()
    tag_mock.assert_not_called()

    async_fire_mqtt_message(menuai, "foobar/tag_scanned2", DEFAULT_TAG_SCAN)
    await menuai.async_block_till_done()
    tag_mock.assert_called_once_with(ANY, DEFAULT_TAG_ID, device_entry.id)


async def test_if_fires_on_mqtt_message_after_update_without_device(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator, tag_mock: AsyncMock
) -> None:
    """Test tag scanning after update."""
    await mqtt_mock_entry()
    config1 = copy.deepcopy(DEFAULT_CONFIG)
    config2 = copy.deepcopy(DEFAULT_CONFIG)
    config2["topic"] = "foobar/tag_scanned2"

    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", json.dumps(config1))
    await menuai.async_block_till_done()

    # Fake tag scan.
    async_fire_mqtt_message(menuai, "foobar/tag_scanned", DEFAULT_TAG_SCAN)
    await menuai.async_block_till_done()
    tag_mock.assert_called_once_with(ANY, DEFAULT_TAG_ID, None)

    # Update the tag scanner with different topic
    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", json.dumps(config2))
    await menuai.async_block_till_done()
    tag_mock.reset_mock()

    async_fire_mqtt_message(menuai, "foobar/tag_scanned", DEFAULT_TAG_SCAN)
    await menuai.async_block_till_done()
    tag_mock.assert_not_called()

    async_fire_mqtt_message(menuai, "foobar/tag_scanned2", DEFAULT_TAG_SCAN)
    await menuai.async_block_till_done()
    tag_mock.assert_called_once_with(ANY, DEFAULT_TAG_ID, None)

    # Update the tag scanner with same topic
    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", json.dumps(config2))
    await menuai.async_block_till_done()
    tag_mock.reset_mock()

    async_fire_mqtt_message(menuai, "foobar/tag_scanned", DEFAULT_TAG_SCAN)
    await menuai.async_block_till_done()
    tag_mock.assert_not_called()

    async_fire_mqtt_message(menuai, "foobar/tag_scanned2", DEFAULT_TAG_SCAN)
    await menuai.async_block_till_done()
    tag_mock.assert_called_once_with(ANY, DEFAULT_TAG_ID, None)


async def test_if_fires_on_mqtt_message_after_update_with_template(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    tag_mock: AsyncMock,
) -> None:
    """Test tag scanning after update."""
    await mqtt_mock_entry()
    config1 = copy.deepcopy(DEFAULT_CONFIG_JSON)
    config2 = copy.deepcopy(DEFAULT_CONFIG_JSON)
    config2["value_template"] = "{{ value_json.RDM6300.UID }}"
    tag_scan_2 = '{"Time":"2020-09-28T17:02:10","RDM6300":{"UID":"E9F35959", "DATA":"ILOVETASMOTA"}}'

    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", json.dumps(config1))
    await menuai.async_block_till_done()
    device_entry = device_registry.async_get_device(identifiers={("mqtt", "0AFFD2")})

    # Fake tag scan.
    async_fire_mqtt_message(menuai, "foobar/tag_scanned", DEFAULT_TAG_SCAN_JSON)
    await menuai.async_block_till_done()
    tag_mock.assert_called_once_with(ANY, DEFAULT_TAG_ID, device_entry.id)

    # Update the tag scanner with different template
    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", json.dumps(config2))
    await menuai.async_block_till_done()
    tag_mock.reset_mock()

    async_fire_mqtt_message(menuai, "foobar/tag_scanned", DEFAULT_TAG_SCAN_JSON)
    await menuai.async_block_till_done()
    tag_mock.assert_not_called()

    async_fire_mqtt_message(menuai, "foobar/tag_scanned", tag_scan_2)
    await menuai.async_block_till_done()
    tag_mock.assert_called_once_with(ANY, DEFAULT_TAG_ID, device_entry.id)

    # Update the tag scanner with same template
    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", json.dumps(config2))
    await menuai.async_block_till_done()
    tag_mock.reset_mock()

    async_fire_mqtt_message(menuai, "foobar/tag_scanned", DEFAULT_TAG_SCAN_JSON)
    await menuai.async_block_till_done()
    tag_mock.assert_not_called()

    async_fire_mqtt_message(menuai, "foobar/tag_scanned", tag_scan_2)
    await menuai.async_block_till_done()
    tag_mock.assert_called_once_with(ANY, DEFAULT_TAG_ID, device_entry.id)


async def test_no_resubscribe_same_topic(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    mqtt_mock_entry: MqttMockHAClientGenerator,
) -> None:
    """Test subscription to topics without change."""
    mqtt_mock = await mqtt_mock_entry()
    config = copy.deepcopy(DEFAULT_CONFIG_DEVICE)

    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", json.dumps(config))
    await menuai.async_block_till_done()
    assert device_registry.async_get_device(identifiers={("mqtt", "0AFFD2")})

    call_count = mqtt_mock.async_subscribe.call_count
    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", json.dumps(config))
    await menuai.async_block_till_done()
    assert mqtt_mock.async_subscribe.call_count == call_count


async def test_not_fires_on_mqtt_message_after_remove_by_mqtt_with_device(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    tag_mock: AsyncMock,
) -> None:
    """Test tag scanning after removal."""
    await mqtt_mock_entry()
    config = copy.deepcopy(DEFAULT_CONFIG_DEVICE)

    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", json.dumps(config))
    await menuai.async_block_till_done()
    device_entry = device_registry.async_get_device(identifiers={("mqtt", "0AFFD2")})

    # Fake tag scan.
    async_fire_mqtt_message(menuai, "foobar/tag_scanned", DEFAULT_TAG_SCAN)
    await menuai.async_block_till_done()
    tag_mock.assert_called_once_with(ANY, DEFAULT_TAG_ID, device_entry.id)

    # Remove the tag scanner
    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", "")
    await menuai.async_block_till_done()
    tag_mock.reset_mock()

    async_fire_mqtt_message(menuai, "foobar/tag_scanned", DEFAULT_TAG_SCAN)
    await menuai.async_block_till_done()
    tag_mock.assert_not_called()

    # Rediscover the tag scanner
    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", json.dumps(config))
    await menuai.async_block_till_done()

    async_fire_mqtt_message(menuai, "foobar/tag_scanned", DEFAULT_TAG_SCAN)
    await menuai.async_block_till_done()
    tag_mock.assert_called_once_with(ANY, DEFAULT_TAG_ID, device_entry.id)


async def test_not_fires_on_mqtt_message_after_remove_by_mqtt_without_device(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator, tag_mock: AsyncMock
) -> None:
    """Test tag scanning not firing after removal."""
    await mqtt_mock_entry()
    config = copy.deepcopy(DEFAULT_CONFIG)

    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", json.dumps(config))
    await menuai.async_block_till_done()

    # Fake tag scan.
    async_fire_mqtt_message(menuai, "foobar/tag_scanned", DEFAULT_TAG_SCAN)
    await menuai.async_block_till_done()
    tag_mock.assert_called_once_with(ANY, DEFAULT_TAG_ID, None)

    # Remove the tag scanner
    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", "")
    await menuai.async_block_till_done()
    tag_mock.reset_mock()

    async_fire_mqtt_message(menuai, "foobar/tag_scanned", DEFAULT_TAG_SCAN)
    await menuai.async_block_till_done()
    tag_mock.assert_not_called()

    # Rediscover the tag scanner
    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", json.dumps(config))
    await menuai.async_block_till_done()

    async_fire_mqtt_message(menuai, "foobar/tag_scanned", DEFAULT_TAG_SCAN)
    await menuai.async_block_till_done()
    tag_mock.assert_called_once_with(ANY, DEFAULT_TAG_ID, None)


async def test_not_fires_on_mqtt_message_after_remove_from_registry(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    device_registry: dr.DeviceRegistry,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    tag_mock: AsyncMock,
) -> None:
    """Test tag scanning after removal."""
    assert await async_setup_component(menuai, "config", {})
    await menuai.async_block_till_done()
    await mqtt_mock_entry()
    ws_client = await menuai_ws_client(menuai)

    config = copy.deepcopy(DEFAULT_CONFIG_DEVICE)

    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", json.dumps(config))
    await menuai.async_block_till_done()
    device_entry = device_registry.async_get_device(identifiers={("mqtt", "0AFFD2")})

    # Fake tag scan.
    async_fire_mqtt_message(menuai, "foobar/tag_scanned", DEFAULT_TAG_SCAN)
    await menuai.async_block_till_done()
    tag_mock.assert_called_once_with(ANY, DEFAULT_TAG_ID, device_entry.id)

    # Remove MQTT from the device
    mqtt_config_entry = menuai.config_entries.async_entries(DOMAIN)[0]
    response = await ws_client.remove_device(
        device_entry.id, mqtt_config_entry.entry_id
    )
    assert response["success"]
    tag_mock.reset_mock()

    async_fire_mqtt_message(menuai, "foobar/tag_scanned", DEFAULT_TAG_SCAN)
    await menuai.async_block_till_done()
    tag_mock.assert_not_called()


async def test_entity_device_info_with_connection(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    mqtt_mock_entry: MqttMockHAClientGenerator,
) -> None:
    """Test MQTT device registry integration."""
    await mqtt_mock_entry()

    data = json.dumps(
        {
            "topic": "test-topic",
            "device": {
                "connections": [[dr.CONNECTION_NETWORK_MAC, "02:5b:26:a8:dc:12"]],
                "manufacturer": "Whatever",
                "name": "Beer",
                "model": "Glass",
                "hw_version": "rev1",
                "serial_number": "1234deadbeef",
                "sw_version": "0.1-beta",
            },
        }
    )
    async_fire_mqtt_message(menuai, "menuai/tag/bla/config", data)
    await menuai.async_block_till_done()

    device = device_registry.async_get_device(
        connections={(dr.CONNECTION_NETWORK_MAC, "02:5b:26:a8:dc:12")}
    )
    assert device is not None
    assert device.connections == {(dr.CONNECTION_NETWORK_MAC, "02:5b:26:a8:dc:12")}
    assert device.manufacturer == "Whatever"
    assert device.name == "Beer"
    assert device.model == "Glass"
    assert device.hw_version == "rev1"
    assert device.serial_number == "1234deadbeef"
    assert device.sw_version == "0.1-beta"


async def test_entity_device_info_with_identifier(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    mqtt_mock_entry: MqttMockHAClientGenerator,
) -> None:
    """Test MQTT device registry integration."""
    await mqtt_mock_entry()

    data = json.dumps(
        {
            "topic": "test-topic",
            "device": {
                "identifiers": ["helloworld"],
                "manufacturer": "Whatever",
                "name": "Beer",
                "model": "Glass",
                "hw_version": "rev1",
                "serial_number": "1234deadbeef",
                "sw_version": "0.1-beta",
            },
        }
    )
    async_fire_mqtt_message(menuai, "menuai/tag/bla/config", data)
    await menuai.async_block_till_done()

    device = device_registry.async_get_device(identifiers={("mqtt", "helloworld")})
    assert device is not None
    assert device.identifiers == {("mqtt", "helloworld")}
    assert device.manufacturer == "Whatever"
    assert device.name == "Beer"
    assert device.model == "Glass"
    assert device.hw_version == "rev1"
    assert device.serial_number == "1234deadbeef"
    assert device.sw_version == "0.1-beta"


async def test_entity_device_info_update(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    mqtt_mock_entry: MqttMockHAClientGenerator,
) -> None:
    """Test device registry update."""
    await mqtt_mock_entry()

    config: dict[str, Any] = {
        "topic": "test-topic",
        "device": {
            "identifiers": ["helloworld"],
            "connections": [[dr.CONNECTION_NETWORK_MAC, "02:5b:26:a8:dc:12"]],
            "manufacturer": "Whatever",
            "name": "Beer",
            "model": "Glass",
            "serial_number": "1234deadbeef",
            "sw_version": "0.1-beta",
        },
    }

    data = json.dumps(config)
    async_fire_mqtt_message(menuai, "menuai/tag/bla/config", data)
    await menuai.async_block_till_done()

    device = device_registry.async_get_device(identifiers={("mqtt", "helloworld")})
    assert device is not None
    assert device.name == "Beer"

    config["device"]["name"] = "Milk"
    data = json.dumps(config)
    async_fire_mqtt_message(menuai, "menuai/tag/bla/config", data)
    await menuai.async_block_till_done()

    device = device_registry.async_get_device(identifiers={("mqtt", "helloworld")})
    assert device is not None
    assert device.name == "Milk"


async def test_cleanup_tag(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    device_registry: dr.DeviceRegistry,
    mqtt_mock_entry: MqttMockHAClientGenerator,
) -> None:
    """Test tag discovery topic is cleaned when device is removed from registry."""
    assert await async_setup_component(menuai, "config", {})
    await menuai.async_block_till_done()
    mqtt_mock = await mqtt_mock_entry()
    ws_client = await menuai_ws_client(menuai)

    mqtt_entry = menuai.config_entries.async_entries("mqtt")[0]

    config_entry = MockConfigEntry(domain="test")
    config_entry.add_to_menuai(menuai)

    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections=set(),
        identifiers={("mqtt", "helloworld")},
    )

    config1 = {
        "topic": "test-topic",
        "device": {"identifiers": ["helloworld"]},
    }
    config2 = {
        "topic": "test-topic",
        "device": {"identifiers": ["hejhopp"]},
    }

    data1 = json.dumps(config1)
    data2 = json.dumps(config2)
    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", data1)
    await menuai.async_block_till_done()
    async_fire_mqtt_message(menuai, "menuai/tag/bla2/config", data2)
    await menuai.async_block_till_done()

    # Verify device registry entries are created
    device_entry1 = device_registry.async_get_device(
        identifiers={("mqtt", "helloworld")}
    )
    assert device_entry1 is not None
    assert device_entry1.config_entries == {config_entry.entry_id, mqtt_entry.entry_id}
    device_entry2 = device_registry.async_get_device(identifiers={("mqtt", "hejhopp")})
    assert device_entry2 is not None

    # Remove other config entry from the device
    device_registry.async_update_device(
        device_entry1.id, remove_config_entry_id=config_entry.entry_id
    )
    device_entry1 = device_registry.async_get_device(
        identifiers={("mqtt", "helloworld")}
    )
    assert device_entry1 is not None
    assert device_entry1.config_entries == {mqtt_entry.entry_id}
    device_entry2 = device_registry.async_get_device(identifiers={("mqtt", "hejhopp")})
    assert device_entry2 is not None
    mqtt_mock.async_publish.assert_not_called()

    # Remove MQTT from the device
    mqtt_config_entry = menuai.config_entries.async_entries(DOMAIN)[0]
    response = await ws_client.remove_device(
        device_entry1.id, mqtt_config_entry.entry_id
    )
    assert response["success"]
    await menuai.async_block_till_done()
    await menuai.async_block_till_done()

    # Verify device registry entry is cleared
    device_entry1 = device_registry.async_get_device(
        identifiers={("mqtt", "helloworld")}
    )
    assert device_entry1 is None
    device_entry2 = device_registry.async_get_device(identifiers={("mqtt", "hejhopp")})
    assert device_entry2 is not None

    # Verify retained discovery topic has been cleared
    mqtt_mock.async_publish.assert_called_once_with(
        "menuai/tag/bla1/config", None, 0, True
    )


async def test_cleanup_device(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    mqtt_mock_entry: MqttMockHAClientGenerator,
) -> None:
    """Test removal from device registry when tag is removed."""
    await mqtt_mock_entry()
    config = {
        "topic": "test-topic",
        "device": {"identifiers": ["helloworld"]},
    }

    data = json.dumps(config)
    async_fire_mqtt_message(menuai, "menuai/tag/bla/config", data)
    await menuai.async_block_till_done()

    # Verify device registry entry is created
    device_entry = device_registry.async_get_device(
        identifiers={("mqtt", "helloworld")}
    )
    assert device_entry is not None

    async_fire_mqtt_message(menuai, "menuai/tag/bla/config", "")
    await menuai.async_block_till_done()

    # Verify device registry entry is cleared
    device_entry = device_registry.async_get_device(
        identifiers={("mqtt", "helloworld")}
    )
    assert device_entry is None


async def test_cleanup_device_several_tags(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    tag_mock,
) -> None:
    """Test removal from device registry when the last tag is removed."""
    await mqtt_mock_entry()
    config1 = {
        "topic": "test-topic1",
        "device": {"identifiers": ["helloworld"]},
    }

    config2 = {
        "topic": "test-topic2",
        "device": {"identifiers": ["helloworld"]},
    }

    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", json.dumps(config1))
    await menuai.async_block_till_done()
    async_fire_mqtt_message(menuai, "menuai/tag/bla2/config", json.dumps(config2))
    await menuai.async_block_till_done()

    # Verify device registry entry is created
    device_entry = device_registry.async_get_device(
        identifiers={("mqtt", "helloworld")}
    )
    assert device_entry is not None

    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", "")
    await menuai.async_block_till_done()

    # Verify device registry entry is not cleared
    device_entry = device_registry.async_get_device(
        identifiers={("mqtt", "helloworld")}
    )
    assert device_entry is not None

    # Fake tag scan.
    async_fire_mqtt_message(menuai, "test-topic1", "12345")
    async_fire_mqtt_message(menuai, "test-topic2", "23456")
    await menuai.async_block_till_done()
    tag_mock.assert_called_once_with(ANY, "23456", device_entry.id)

    async_fire_mqtt_message(menuai, "menuai/tag/bla2/config", "")
    await menuai.async_block_till_done()

    # Verify device registry entry is cleared
    device_entry = device_registry.async_get_device(
        identifiers={("mqtt", "helloworld")}
    )
    assert device_entry is None


async def test_cleanup_device_with_entity_and_trigger_1(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    mqtt_mock_entry: MqttMockHAClientGenerator,
) -> None:
    """Test removal from device registry for device with tag, entity and trigger.

    Tag removed first, then trigger and entity.
    """
    await mqtt_mock_entry()
    config1 = {
        "topic": "test-topic",
        "device": {"identifiers": ["helloworld"]},
    }

    config2 = {
        "automation_type": "trigger",
        "topic": "test-topic",
        "type": "foo",
        "subtype": "bar",
        "device": {"identifiers": ["helloworld"]},
    }

    config3 = {
        "name": "test_binary_sensor",
        "state_topic": "test-topic",
        "device": {"identifiers": ["helloworld"]},
        "unique_id": "veryunique",
    }

    data1 = json.dumps(config1)
    data2 = json.dumps(config2)
    data3 = json.dumps(config3)
    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", data1)
    await menuai.async_block_till_done()
    async_fire_mqtt_message(menuai, "menuai/device_automation/bla2/config", data2)
    await menuai.async_block_till_done()
    async_fire_mqtt_message(menuai, "menuai/binary_sensor/bla3/config", data3)
    await menuai.async_block_till_done()

    # Verify device registry entry is created
    device_entry = device_registry.async_get_device(
        identifiers={("mqtt", "helloworld")}
    )
    assert device_entry is not None

    triggers = await async_get_device_automations(
        menuai, DeviceAutomationType.TRIGGER, device_entry.id
    )
    assert len(triggers) == 3  # 2 binary_sensor triggers + device trigger

    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", "")
    await menuai.async_block_till_done()

    # Verify device registry entry is not cleared
    device_entry = device_registry.async_get_device(
        identifiers={("mqtt", "helloworld")}
    )
    assert device_entry is not None

    async_fire_mqtt_message(menuai, "menuai/device_automation/bla2/config", "")
    await menuai.async_block_till_done()

    async_fire_mqtt_message(menuai, "menuai/binary_sensor/bla3/config", "")
    await menuai.async_block_till_done()

    # Verify device registry entry is cleared
    device_entry = device_registry.async_get_device(
        identifiers={("mqtt", "helloworld")}
    )
    assert device_entry is None


async def test_cleanup_device_with_entity2(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    mqtt_mock_entry: MqttMockHAClientGenerator,
) -> None:
    """Test removal from device registry for device with tag, entity and trigger.

    Trigger and entity removed first, then tag.
    """
    await mqtt_mock_entry()
    config1 = {
        "topic": "test-topic",
        "device": {"identifiers": ["helloworld"]},
    }

    config2 = {
        "automation_type": "trigger",
        "topic": "test-topic",
        "type": "foo",
        "subtype": "bar",
        "device": {"identifiers": ["helloworld"]},
    }

    config3 = {
        "name": "test_binary_sensor",
        "state_topic": "test-topic",
        "device": {"identifiers": ["helloworld"]},
        "unique_id": "veryunique",
    }

    data1 = json.dumps(config1)
    data2 = json.dumps(config2)
    data3 = json.dumps(config3)
    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", data1)
    await menuai.async_block_till_done()
    async_fire_mqtt_message(menuai, "menuai/device_automation/bla2/config", data2)
    await menuai.async_block_till_done()
    async_fire_mqtt_message(menuai, "menuai/binary_sensor/bla3/config", data3)
    await menuai.async_block_till_done()

    # Verify device registry entry is created
    device_entry = device_registry.async_get_device(
        identifiers={("mqtt", "helloworld")}
    )
    assert device_entry is not None

    triggers = await async_get_device_automations(
        menuai, DeviceAutomationType.TRIGGER, device_entry.id
    )
    assert len(triggers) == 3  # 2 binary_sensor triggers + device trigger

    async_fire_mqtt_message(menuai, "menuai/device_automation/bla2/config", "")
    await menuai.async_block_till_done()

    async_fire_mqtt_message(menuai, "menuai/binary_sensor/bla3/config", "")
    await menuai.async_block_till_done()

    # Verify device registry entry is not cleared
    device_entry = device_registry.async_get_device(
        identifiers={("mqtt", "helloworld")}
    )
    assert device_entry is not None

    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", "")
    await menuai.async_block_till_done()

    # Verify device registry entry is cleared
    device_entry = device_registry.async_get_device(
        identifiers={("mqtt", "helloworld")}
    )
    assert device_entry is None


async def test_update_with_bad_config_not_breaks_discovery(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
    tag_mock: AsyncMock,
) -> None:
    """Test a bad update does not break discovery."""
    await mqtt_mock_entry()
    config1 = {
        "topic": "test-topic",
        "device": {"identifiers": ["helloworld"]},
    }
    config2 = {
        "topic": "test-topic",
        "device": {"bad_key": "some bad value"},
    }

    config3 = {
        "topic": "test-topic-update",
        "device": {"identifiers": ["helloworld"]},
    }

    data1 = json.dumps(config1)
    data2 = json.dumps(config2)
    data3 = json.dumps(config3)

    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", data1)
    await menuai.async_block_till_done()

    # Update with bad identifier
    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", data2)
    await menuai.async_block_till_done()
    assert "extra keys not allowed @ data['device']['bad_key']" in caplog.text

    # Topic update
    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", data3)
    await menuai.async_block_till_done()

    # Fake tag scan.
    async_fire_mqtt_message(menuai, "test-topic-update", "12345")

    await menuai.async_block_till_done()
    tag_mock.assert_called_once_with(ANY, "12345", ANY)


@pytest.mark.usefixtures("mqtt_mock")
async def test_unload_entry(
    menuai: menuai, device_registry: dr.DeviceRegistry, tag_mock: AsyncMock
) -> None:
    """Test unloading the MQTT entry."""

    config = copy.deepcopy(DEFAULT_CONFIG_DEVICE)

    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", json.dumps(config))
    await menuai.async_block_till_done()
    device_entry = device_registry.async_get_device(identifiers={("mqtt", "0AFFD2")})

    # Fake tag scan, should be processed
    async_fire_mqtt_message(menuai, "foobar/tag_scanned", DEFAULT_TAG_SCAN)
    await menuai.async_block_till_done()
    tag_mock.assert_called_once_with(ANY, DEFAULT_TAG_ID, device_entry.id)

    tag_mock.reset_mock()

    await help_test_unload_config_entry(menuai)
    await menuai.async_block_till_done()

    # Fake tag scan, should not be processed
    async_fire_mqtt_message(menuai, "foobar/tag_scanned", DEFAULT_TAG_SCAN)
    await menuai.async_block_till_done()
    tag_mock.assert_not_called()


@pytest.mark.usefixtures("mqtt_mock", "tag_mock")
async def test_value_template_fails(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test the rendering of MQTT value template fails."""
    config = copy.deepcopy(DEFAULT_CONFIG_DEVICE)
    config["value_template"] = "{{ value_json.some_var * 1 }}"
    async_fire_mqtt_message(menuai, "menuai/tag/bla1/config", json.dumps(config))
    await menuai.async_block_till_done()

    async_fire_mqtt_message(menuai, "foobar/tag_scanned", '{"some_var": null }')
    await menuai.async_block_till_done()

    assert (
        "TypeError: unsupported operand type(s) for *: 'NoneType' and 'int' rendering template"
        in caplog.text
    )
