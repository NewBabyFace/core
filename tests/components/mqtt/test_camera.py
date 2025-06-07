"""The tests for mqtt camera component."""

from base64 import b64encode
from http import HTTPStatus
import json
from unittest.mock import patch

import pytest

from menuai.components import camera, mqtt
from menuai.components.mqtt.camera import MQTT_CAMERA_ATTRIBUTES_BLOCKED
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
    help_test_entity_id_update_discovery_update,
    help_test_entity_id_update_subscriptions,
    help_test_reloadable,
    help_test_setting_attribute_via_mqtt_json_message,
    help_test_setting_attribute_with_template,
    help_test_setting_blocked_attribute_via_mqtt_json_message,
    help_test_unique_id,
    help_test_unload_config_entry_with_platform,
    help_test_update_with_json_attrs_bad_json,
    help_test_update_with_json_attrs_not_dict,
)

from tests.common import async_fire_mqtt_message
from tests.typing import (
    ClientSessionGenerator,
    MqttMockHAClientGenerator,
    MqttMockPahoClient,
)

DEFAULT_CONFIG = {mqtt.DOMAIN: {camera.DOMAIN: {"name": "test", "topic": "test_topic"}}}


@pytest.mark.parametrize(
    "menuai_config",
    [{mqtt.DOMAIN: {camera.DOMAIN: {"topic": "test/camera", "name": "Test Camera"}}}],
)
async def test_run_camera_setup(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    mqtt_mock_entry: MqttMockHAClientGenerator,
) -> None:
    """Test that it fetches the given payload."""
    topic = "test/camera"
    await mqtt_mock_entry()

    url = menuai.states.get("camera.test_camera").attributes["entity_picture"]

    async_fire_mqtt_message(menuai, topic, "beer")

    client = await menuai_client_no_auth()
    resp = await client.get(url)
    assert resp.status == HTTPStatus.OK
    body = await resp.text()
    assert body == "beer"


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                camera.DOMAIN: {
                    "topic": "test/camera",
                    "name": "Test Camera",
                    "image_encoding": "b64",
                }
            }
        }
    ],
)
async def test_run_camera_b64_encoded(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    mqtt_mock_entry: MqttMockHAClientGenerator,
) -> None:
    """Test that it fetches the given encoded payload."""
    topic = "test/camera"
    await mqtt_mock_entry()

    url = menuai.states.get("camera.test_camera").attributes["entity_picture"]

    async_fire_mqtt_message(menuai, topic, b64encode(b"grass"))

    client = await menuai_client_no_auth()
    resp = await client.get(url)
    assert resp.status == HTTPStatus.OK
    body = await resp.text()
    assert body == "grass"


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                "camera": {
                    "topic": "test/camera",
                    "name": "Test Camera",
                    "encoding": "utf-8",
                    "image_encoding": "b64",
                    "availability": {"topic": "test/camera_availability"},
                }
            }
        }
    ],
)
async def test_camera_b64_encoded_with_availability(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    mqtt_mock_entry: MqttMockHAClientGenerator,
) -> None:
    """Test availability works if b64 encoding is turned on."""
    topic = "test/camera"
    topic_availability = "test/camera_availability"
    await mqtt_mock_entry()

    # Make sure we are available
    async_fire_mqtt_message(menuai, topic_availability, "online")

    url = menuai.states.get("camera.test_camera").attributes["entity_picture"]

    async_fire_mqtt_message(menuai, topic, b64encode(b"grass"))

    client = await menuai_client_no_auth()
    resp = await client.get(url)
    assert resp.status == HTTPStatus.OK
    body = await resp.text()
    assert body == "grass"


@pytest.mark.parametrize("menuai_config", [DEFAULT_CONFIG])
async def test_availability_when_connection_lost(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test availability after MQTT disconnection."""
    await help_test_availability_when_connection_lost(
        menuai, mqtt_mock_entry, camera.DOMAIN
    )


@pytest.mark.parametrize("menuai_config", [DEFAULT_CONFIG])
async def test_availability_without_topic(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test availability without defined availability topic."""
    await help_test_availability_without_topic(
        menuai, mqtt_mock_entry, camera.DOMAIN, DEFAULT_CONFIG
    )


async def test_default_availability_payload(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test availability by default payload with defined topic."""
    await help_test_default_availability_payload(
        menuai, mqtt_mock_entry, camera.DOMAIN, DEFAULT_CONFIG
    )


async def test_custom_availability_payload(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test availability by custom payload with defined topic."""
    await help_test_custom_availability_payload(
        menuai, mqtt_mock_entry, camera.DOMAIN, DEFAULT_CONFIG
    )


async def test_setting_attribute_via_mqtt_json_message(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the setting of attribute via MQTT with JSON payload."""
    await help_test_setting_attribute_via_mqtt_json_message(
        menuai, mqtt_mock_entry, camera.DOMAIN, DEFAULT_CONFIG
    )


async def test_setting_blocked_attribute_via_mqtt_json_message(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the setting of attribute via MQTT with JSON payload."""
    await help_test_setting_blocked_attribute_via_mqtt_json_message(
        menuai,
        mqtt_mock_entry,
        camera.DOMAIN,
        DEFAULT_CONFIG,
        MQTT_CAMERA_ATTRIBUTES_BLOCKED,
    )


async def test_setting_attribute_with_template(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the setting of attribute via MQTT with JSON payload."""
    await help_test_setting_attribute_with_template(
        menuai, mqtt_mock_entry, camera.DOMAIN, DEFAULT_CONFIG
    )


async def test_update_with_json_attrs_not_dict(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test attributes get extracted from a JSON result."""
    await help_test_update_with_json_attrs_not_dict(
        menuai, mqtt_mock_entry, caplog, camera.DOMAIN, DEFAULT_CONFIG
    )


async def test_update_with_json_attrs_bad_json(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test attributes get extracted from a JSON result."""
    await help_test_update_with_json_attrs_bad_json(
        menuai, mqtt_mock_entry, caplog, camera.DOMAIN, DEFAULT_CONFIG
    )


async def test_discovery_update_attr(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test update of discovered MQTTAttributes."""
    await help_test_discovery_update_attr(
        menuai, mqtt_mock_entry, camera.DOMAIN, DEFAULT_CONFIG
    )


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                camera.DOMAIN: [
                    {
                        "name": "Test 1",
                        "topic": "test-topic",
                        "unique_id": "TOTALLY_UNIQUE",
                    },
                    {
                        "name": "Test 2",
                        "topic": "test-topic",
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
    """Test unique id option only creates one camera per unique_id."""
    await help_test_unique_id(menuai, mqtt_mock_entry, camera.DOMAIN)


async def test_discovery_removal_camera(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test removal of discovered camera."""
    data = json.dumps(DEFAULT_CONFIG[mqtt.DOMAIN][camera.DOMAIN])
    await help_test_discovery_removal(menuai, mqtt_mock_entry, camera.DOMAIN, data)


async def test_discovery_update_camera(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
) -> None:
    """Test update of discovered camera."""
    config1 = {"name": "Beer", "topic": "test_topic"}
    config2 = {"name": "Milk", "topic": "test_topic"}

    await help_test_discovery_update(
        menuai, mqtt_mock_entry, camera.DOMAIN, config1, config2
    )


async def test_discovery_update_unchanged_camera(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test update of discovered camera."""
    data1 = '{ "name": "Beer", "topic": "test_topic"}'
    with patch(
        "menuai.components.mqtt.camera.MqttCamera.discovery_update"
    ) as discovery_update:
        await help_test_discovery_update_unchanged(
            menuai, mqtt_mock_entry, camera.DOMAIN, data1, discovery_update
        )


@pytest.mark.no_fail_on_log_exception
async def test_discovery_broken(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test handling of bad discovery message."""
    data1 = '{ "name": "Beer" }'
    data2 = '{ "name": "Milk", "topic": "test_topic"}'

    await help_test_discovery_broken(menuai, mqtt_mock_entry, camera.DOMAIN, data1, data2)


async def test_entity_device_info_with_connection(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT camera device registry integration."""
    await help_test_entity_device_info_with_connection(
        menuai, mqtt_mock_entry, camera.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_device_info_with_identifier(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT camera device registry integration."""
    await help_test_entity_device_info_with_identifier(
        menuai, mqtt_mock_entry, camera.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_device_info_update(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test device registry update."""
    await help_test_entity_device_info_update(
        menuai, mqtt_mock_entry, camera.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_device_info_remove(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test device registry remove."""
    await help_test_entity_device_info_remove(
        menuai, mqtt_mock_entry, camera.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_id_update_subscriptions(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT subscriptions are managed when entity_id is updated."""
    await help_test_entity_id_update_subscriptions(
        menuai, mqtt_mock_entry, camera.DOMAIN, DEFAULT_CONFIG, ["test_topic"]
    )


async def test_entity_id_update_discovery_update(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT discovery update when entity_id is updated."""
    await help_test_entity_id_update_discovery_update(
        menuai, mqtt_mock_entry, camera.DOMAIN, DEFAULT_CONFIG
    )


async def test_entity_debug_info_message(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test MQTT debug info."""
    await help_test_entity_debug_info_message(
        menuai,
        mqtt_mock_entry,
        camera.DOMAIN,
        DEFAULT_CONFIG,
        None,
        state_topic="test_topic",
        state_payload=b"ON",
    )


async def test_reloadable(
    menuai: menuai, mqtt_client_mock: MqttMockPahoClient
) -> None:
    """Test reloading the MQTT platform."""
    domain = camera.DOMAIN
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
    platform = camera.DOMAIN
    assert menuai.states.get(f"{platform}.test")


async def test_unload_entry(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test unloading the config entry."""
    domain = camera.DOMAIN
    config = DEFAULT_CONFIG
    await help_test_unload_config_entry_with_platform(
        menuai, mqtt_mock_entry, domain, config
    )
