"""The tests for the MQTT device_tracker platform."""

from datetime import UTC, datetime

from freezegun.api import FrozenDateTimeFactory
import pytest

from menuai.components import device_tracker, mqtt
from menuai.components.mqtt.const import DOMAIN
from menuai.const import STATE_HOME, STATE_NOT_HOME, STATE_UNKNOWN
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.setup import async_setup_component

from .common import (
    help_custom_config,
    help_test_reloadable,
    help_test_setting_blocked_attribute_via_mqtt_json_message,
    help_test_skipped_async_ha_write_state,
)

from tests.common import async_fire_mqtt_message
from tests.typing import (
    MqttMockHAClientGenerator,
    MqttMockPahoClient,
    WebSocketGenerator,
)

DEFAULT_CONFIG = {
    mqtt.DOMAIN: {
        device_tracker.DOMAIN: {
            "name": "test",
            "state_topic": "test-topic",
        }
    }
}


async def test_discover_device_tracker(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test discovering an MQTT device tracker component."""
    await mqtt_mock_entry()
    async_fire_mqtt_message(
        menuai,
        "menuai/device_tracker/bla/config",
        '{ "name": "test", "state_topic": "test_topic" }',
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("device_tracker.test")

    assert state is not None
    assert state.name == "test"
    assert ("device_tracker", "bla") in menuai.data["mqtt"].discovery_already_discovered


@pytest.mark.no_fail_on_log_exception
async def test_discovery_broken(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test handling of bad discovery message."""
    await mqtt_mock_entry()
    async_fire_mqtt_message(
        menuai,
        "menuai/device_tracker/bla/config",
        '{ "name": "Beer" }',
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("device_tracker.beer")
    assert state is None

    async_fire_mqtt_message(
        menuai,
        "menuai/device_tracker/bla/config",
        '{ "name": "Beer", "state_topic": "required-topic" }',
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("device_tracker.beer")
    assert state is not None
    assert state.name == "Beer"


async def test_non_duplicate_device_tracker_discovery(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test for a non duplicate component."""
    await mqtt_mock_entry()
    async_fire_mqtt_message(
        menuai,
        "menuai/device_tracker/bla/config",
        '{ "name": "Beer", "state_topic": "test-topic" }',
    )
    async_fire_mqtt_message(
        menuai,
        "menuai/device_tracker/bla/config",
        '{ "name": "Beer", "state_topic": "test-topic" }',
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("device_tracker.beer")
    state_duplicate = menuai.states.get("device_tracker.beer1")

    assert state is not None
    assert state.name == "Beer"
    assert state_duplicate is None
    assert "Component has already been discovered: device_tracker bla" in caplog.text


async def test_device_tracker_removal(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test removal of component through empty discovery message."""
    await mqtt_mock_entry()
    async_fire_mqtt_message(
        menuai,
        "menuai/device_tracker/bla/config",
        '{ "name": "Beer", "state_topic": "test-topic" }',
    )
    await menuai.async_block_till_done()
    state = menuai.states.get("device_tracker.beer")
    assert state is not None

    async_fire_mqtt_message(menuai, "menuai/device_tracker/bla/config", "")
    await menuai.async_block_till_done()
    state = menuai.states.get("device_tracker.beer")
    assert state is None


async def test_device_tracker_rediscover(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test rediscover of removed component."""
    await mqtt_mock_entry()
    async_fire_mqtt_message(
        menuai,
        "menuai/device_tracker/bla/config",
        '{ "name": "Beer", "state_topic": "test-topic" }',
    )
    await menuai.async_block_till_done()
    state = menuai.states.get("device_tracker.beer")
    assert state is not None

    async_fire_mqtt_message(menuai, "menuai/device_tracker/bla/config", "")
    await menuai.async_block_till_done()
    state = menuai.states.get("device_tracker.beer")
    assert state is None

    async_fire_mqtt_message(
        menuai,
        "menuai/device_tracker/bla/config",
        '{ "name": "Beer", "state_topic": "test-topic" }',
    )
    await menuai.async_block_till_done()
    state = menuai.states.get("device_tracker.beer")
    assert state is not None


async def test_duplicate_device_tracker_removal(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test for a non duplicate component."""
    await mqtt_mock_entry()
    async_fire_mqtt_message(
        menuai,
        "menuai/device_tracker/bla/config",
        '{ "name": "Beer", "state_topic": "test-topic" }',
    )
    await menuai.async_block_till_done()
    async_fire_mqtt_message(menuai, "menuai/device_tracker/bla/config", "")
    await menuai.async_block_till_done()
    assert "Component has already been discovered: device_tracker bla" in caplog.text
    caplog.clear()
    async_fire_mqtt_message(menuai, "menuai/device_tracker/bla/config", "")
    await menuai.async_block_till_done()

    assert (
        "Component has already been discovered: device_tracker bla" not in caplog.text
    )


async def test_device_tracker_discovery_update(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test for a discovery update event."""
    freezer.move_to("2023-08-22 19:15:00+00:00")
    await mqtt_mock_entry()
    async_fire_mqtt_message(
        menuai,
        "menuai/device_tracker/bla/config",
        '{ "name": "Beer", "state_topic": "test-topic" }',
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("device_tracker.beer")
    assert state is not None
    assert state.name == "Beer"
    assert state.last_updated == datetime(2023, 8, 22, 19, 15, tzinfo=UTC)

    freezer.move_to("2023-08-22 19:16:00+00:00")
    async_fire_mqtt_message(
        menuai,
        "menuai/device_tracker/bla/config",
        '{ "name": "Cider", "state_topic": "test-topic" }',
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("device_tracker.beer")
    assert state is not None
    assert state.name == "Cider"
    assert state.last_updated == datetime(2023, 8, 22, 19, 16, tzinfo=UTC)

    freezer.move_to("2023-08-22 19:20:00+00:00")
    async_fire_mqtt_message(
        menuai,
        "menuai/device_tracker/bla/config",
        '{ "name": "Cider", "state_topic": "test-topic" }',
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("device_tracker.beer")
    assert state is not None
    assert state.name == "Cider"
    # Entity was not updated as the state was not changed
    assert state.last_updated == datetime(2023, 8, 22, 19, 16, tzinfo=UTC)

    await menuai.async_block_till_done(wait_background_tasks=True)


async def test_cleanup_device_tracker(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    mqtt_mock_entry: MqttMockHAClientGenerator,
) -> None:
    """Test discovered device is cleaned up when removed from registry."""
    assert await async_setup_component(menuai, "config", {})
    await menuai.async_block_till_done()
    mqtt_mock = await mqtt_mock_entry()
    ws_client = await menuai_ws_client(menuai)

    async_fire_mqtt_message(
        menuai,
        "menuai/device_tracker/bla/config",
        '{ "device":{"identifiers":["0AFFD2"]},'
        '  "state_topic": "foobar/tracker",'
        '  "unique_id": "unique" }',
    )
    await menuai.async_block_till_done()

    # Verify device and registry entries are created
    device_entry = device_registry.async_get_device(identifiers={("mqtt", "0AFFD2")})
    assert device_entry is not None
    entity_entry = entity_registry.async_get("device_tracker.mqtt_unique")
    assert entity_entry is not None

    state = menuai.states.get("device_tracker.mqtt_unique")
    assert state is not None

    # Remove MQTT from the device
    mqtt_config_entry = menuai.config_entries.async_entries(DOMAIN)[0]
    response = await ws_client.remove_device(
        device_entry.id, mqtt_config_entry.entry_id
    )
    assert response["success"]
    await menuai.async_block_till_done()
    await menuai.async_block_till_done()

    # Verify device and registry entries are cleared
    device_entry = device_registry.async_get_device(identifiers={("mqtt", "0AFFD2")})
    assert device_entry is None
    entity_entry = entity_registry.async_get("device_tracker.mqtt_unique")
    assert entity_entry is None

    # Verify state is removed
    state = menuai.states.get("device_tracker.mqtt_unique")
    assert state is None
    await menuai.async_block_till_done()

    # Verify retained discovery topic has been cleared
    mqtt_mock.async_publish.assert_called_once_with(
        "menuai/device_tracker/bla/config", None, 0, True
    )


async def test_setting_device_tracker_value_via_mqtt_message(
    menuai: menuai,
    mqtt_mock_entry: MqttMockHAClientGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the setting of the value via MQTT."""
    await mqtt_mock_entry()
    async_fire_mqtt_message(
        menuai,
        "menuai/device_tracker/bla/config",
        '{ "name": "test", "state_topic": "test-topic" }',
    )

    await menuai.async_block_till_done()

    state = menuai.states.get("device_tracker.test")

    assert state.state == STATE_UNKNOWN

    async_fire_mqtt_message(menuai, "test-topic", "home")
    state = menuai.states.get("device_tracker.test")
    assert state.state == STATE_HOME

    async_fire_mqtt_message(menuai, "test-topic", "not_home")
    state = menuai.states.get("device_tracker.test")
    assert state.state == STATE_NOT_HOME

    # Test an empty value is ignored and the state is retained
    async_fire_mqtt_message(menuai, "test-topic", "")
    state = menuai.states.get("device_tracker.test")
    assert state.state == STATE_NOT_HOME


async def test_setting_device_tracker_value_via_mqtt_message_and_template(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the setting of the value via MQTT."""
    await mqtt_mock_entry()
    async_fire_mqtt_message(
        menuai,
        "menuai/device_tracker/bla/config",
        "{"
        '"name": "test", '
        '"state_topic": "test-topic", '
        '"value_template": "{% if value is equalto \\"proxy_for_home\\" %}home{% else %}not_home{% endif %}" '
        "}",
    )
    await menuai.async_block_till_done()

    async_fire_mqtt_message(menuai, "test-topic", "proxy_for_home")
    state = menuai.states.get("device_tracker.test")
    assert state.state == STATE_HOME

    async_fire_mqtt_message(menuai, "test-topic", "anything_for_not_home")
    state = menuai.states.get("device_tracker.test")
    assert state.state == STATE_NOT_HOME


async def test_setting_device_tracker_value_via_mqtt_message_and_template2(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the setting of the value via MQTT."""
    await mqtt_mock_entry()
    async_fire_mqtt_message(
        menuai,
        "menuai/device_tracker/bla/config",
        "{"
        '"name": "test", '
        '"state_topic": "test-topic", '
        '"value_template": "{{ value | lower }}" '
        "}",
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("device_tracker.test")
    assert state.state == STATE_UNKNOWN

    async_fire_mqtt_message(menuai, "test-topic", "HOME")
    state = menuai.states.get("device_Tracker.test")
    assert state.state == STATE_HOME

    async_fire_mqtt_message(menuai, "test-topic", "NOT_HOME")
    state = menuai.states.get("device_tracker.test")
    assert state.state == STATE_NOT_HOME


async def test_setting_device_tracker_location_via_mqtt_message(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the setting of the location via MQTT."""
    await mqtt_mock_entry()
    async_fire_mqtt_message(
        menuai,
        "menuai/device_tracker/bla/config",
        '{ "name": "test", "state_topic": "test-topic", "source_type": "router" }',
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("device_tracker.test")
    assert state.attributes["source_type"] == "router"

    assert state.state == STATE_UNKNOWN

    async_fire_mqtt_message(menuai, "test-topic", "test-location")
    state = menuai.states.get("device_tracker.test")
    assert state.state == "test-location"


async def test_setting_device_tracker_location_via_lat_lon_message(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the setting of the latitude and longitude via MQTT without state topic."""
    await mqtt_mock_entry()
    async_fire_mqtt_message(
        menuai,
        "menuai/device_tracker/bla/config",
        '{ "name": "test", "json_attributes_topic": "attributes-topic"}',
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("device_tracker.test")
    assert state.attributes["source_type"] == "gps"

    assert state.state == STATE_UNKNOWN

    menuai.config.latitude = 32.87336
    menuai.config.longitude = -117.22743

    async_fire_mqtt_message(
        menuai,
        "attributes-topic",
        '{"latitude":32.87336,"longitude": -117.22743, "gps_accuracy":1.5, "source_type": "router"}',
    )
    state = menuai.states.get("device_tracker.test")
    assert state.attributes["latitude"] == 32.87336
    assert state.attributes["longitude"] == -117.22743
    assert state.attributes["gps_accuracy"] == 1.5
    # assert source_type is overridden by discovery
    assert state.attributes["source_type"] == "router"
    assert state.state == STATE_HOME

    async_fire_mqtt_message(
        menuai,
        "attributes-topic",
        '{"latitude":50.1,"longitude": -2.1}',
    )
    state = menuai.states.get("device_tracker.test")
    assert state.attributes["latitude"] == 50.1
    assert state.attributes["longitude"] == -2.1
    assert state.attributes["gps_accuracy"] == 0
    assert state.attributes["source_type"] == "gps"
    assert state.state == STATE_NOT_HOME

    # incomplete coordinates results in unknown state
    async_fire_mqtt_message(menuai, "attributes-topic", '{"longitude": -117.22743}')
    state = menuai.states.get("device_tracker.test")
    assert "latitude" not in state.attributes
    assert "longitude" not in state.attributes
    assert state.attributes["source_type"] == "gps"
    assert state.state == STATE_UNKNOWN

    async_fire_mqtt_message(menuai, "attributes-topic", '{"latitude":32.87336}')
    state = menuai.states.get("device_tracker.test")
    assert "latitude" not in state.attributes
    assert "longitude" not in state.attributes
    assert state.attributes["source_type"] == "gps"
    assert state.state == STATE_UNKNOWN

    # invalid coordinates results in unknown state
    async_fire_mqtt_message(
        menuai, "attributes-topic", '{"longitude": -117.22743, "latitude":null}'
    )
    state = menuai.states.get("device_tracker.test")
    assert "latitude" not in state.attributes
    assert "longitude" not in state.attributes
    assert state.attributes["source_type"] == "gps"
    assert state.state == STATE_UNKNOWN

    # Test number validation
    async_fire_mqtt_message(
        menuai,
        "attributes-topic",
        '{"latitude": "32.87336","longitude": "-117.22743", "gps_accuracy": "1.5", "source_type": "router"}',
    )
    state = menuai.states.get("device_tracker.test")
    assert "latitude" not in state.attributes
    assert "longitude" not in state.attributes
    assert "gps_accuracy" not in state.attributes
    # assert source_type is overridden by discovery
    assert state.attributes["source_type"] == "router"
    assert state.state == STATE_UNKNOWN

    # Test with invalid GPS accuracy should default to 0,
    # but location updates as expected
    async_fire_mqtt_message(
        menuai,
        "attributes-topic",
        '{"latitude": 32.871234,"longitude": -117.21234, "gps_accuracy": "invalid", "source_type": "router"}',
    )
    state = menuai.states.get("device_tracker.test")
    assert state.state == STATE_NOT_HOME
    assert state.attributes["latitude"] == 32.871234
    assert state.attributes["longitude"] == -117.21234
    assert state.attributes["gps_accuracy"] == 0
    assert state.attributes["source_type"] == "router"

    # Test with invalid latitude
    async_fire_mqtt_message(
        menuai,
        "attributes-topic",
        '{"latitude": null,"longitude": "-117.22743", "gps_accuracy": 1, "source_type": "router"}',
    )
    state = menuai.states.get("device_tracker.test")
    assert "latitude" not in state.attributes
    assert "longitude" not in state.attributes
    assert state.state == STATE_UNKNOWN

    # Test with invalid longitude
    async_fire_mqtt_message(
        menuai,
        "attributes-topic",
        '{"latitude": 32.87336,"longitude": "unknown", "gps_accuracy": 1, "source_type": "router"}',
    )
    state = menuai.states.get("device_tracker.test")
    assert "latitude" not in state.attributes
    assert "longitude" not in state.attributes
    assert state.state == STATE_UNKNOWN


async def test_setting_device_tracker_location_via_reset_message(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the automatic inference of zones via MQTT via reset."""
    await mqtt_mock_entry()
    async_fire_mqtt_message(
        menuai,
        "menuai/device_tracker/bla/config",
        "{ "
        '"name": "test", '
        '"state_topic": "test-topic", '
        '"json_attributes_topic": "attributes-topic" '
        "}",
    )

    menuai.states.async_set(
        "zone.school",
        "zoning",
        {
            "latitude": 30.0,
            "longitude": -100.0,
            "radius": 100,
            "friendly_name": "School",
        },
    )

    await menuai.async_block_till_done()

    state = menuai.states.get("device_tracker.test")
    assert state.attributes["source_type"] == "gps"

    assert state.state == STATE_UNKNOWN

    menuai.config.latitude = 32.87336
    menuai.config.longitude = -117.22743

    # test reset and gps attributes
    async_fire_mqtt_message(
        menuai,
        "attributes-topic",
        '{"latitude":32.87336,"longitude": -117.22743, "gps_accuracy":1.5}',
    )
    async_fire_mqtt_message(menuai, "test-topic", "None")

    state = menuai.states.get("device_tracker.test")
    assert state.attributes["latitude"] == 32.87336
    assert state.attributes["longitude"] == -117.22743
    assert state.attributes["gps_accuracy"] == 1.5
    assert state.attributes["source_type"] == "gps"
    assert state.state == STATE_HOME

    # test manual state override
    async_fire_mqtt_message(menuai, "test-topic", "Work")

    state = menuai.states.get("device_tracker.test")
    assert state.state == "Work"

    # test reset
    async_fire_mqtt_message(menuai, "test-topic", "None")

    state = menuai.states.get("device_tracker.test")
    assert state.state == STATE_HOME

    # test reset inferring correct school area
    async_fire_mqtt_message(
        menuai,
        "attributes-topic",
        '{"latitude":30.0,"longitude":-100.0,"gps_accuracy":1.5}',
    )

    state = menuai.states.get("device_tracker.test")
    assert state.state == "School"


async def test_setting_device_tracker_location_via_abbr_reset_message(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the setting of reset via abbreviated names and custom payloads via MQTT."""
    await mqtt_mock_entry()
    async_fire_mqtt_message(
        menuai,
        "menuai/device_tracker/bla/config",
        "{ "
        '"name": "test", '
        '"state_topic": "test-topic", '
        '"json_attributes_topic": "attributes-topic", '
        '"pl_rst": "reset" '
        "}",
    )

    await menuai.async_block_till_done()

    state = menuai.states.get("device_tracker.test")
    assert state.attributes["source_type"] == "gps"

    assert state.state == STATE_UNKNOWN

    menuai.config.latitude = 32.87336
    menuai.config.longitude = -117.22743

    # test custom reset payload and gps attributes
    async_fire_mqtt_message(
        menuai,
        "attributes-topic",
        '{"latitude":32.87336,"longitude": -117.22743, "gps_accuracy":1.5}',
    )
    async_fire_mqtt_message(menuai, "test-topic", "reset")

    state = menuai.states.get("device_tracker.test")
    assert state.attributes["latitude"] == 32.87336
    assert state.attributes["longitude"] == -117.22743
    assert state.attributes["gps_accuracy"] == 1.5
    assert state.attributes["source_type"] == "gps"
    assert state.state == STATE_HOME


async def test_setting_blocked_attribute_via_mqtt_json_message(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test the setting of attribute via MQTT with JSON payload."""
    await help_test_setting_blocked_attribute_via_mqtt_json_message(
        menuai, mqtt_mock_entry, device_tracker.DOMAIN, DEFAULT_CONFIG, None
    )


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            mqtt.DOMAIN: {
                device_tracker.DOMAIN: {"name": "jan", "state_topic": "/location/jan"}
            }
        }
    ],
)
async def test_setup_with_modern_schema(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> None:
    """Test setup using the modern schema."""
    await mqtt_mock_entry()
    dev_id = "jan"
    entity_id = f"{device_tracker.DOMAIN}.{dev_id}"
    assert menuai.states.get(entity_id) is not None


async def test_reloadable(
    menuai: menuai, mqtt_client_mock: MqttMockPahoClient
) -> None:
    """Test reloading the MQTT platform."""
    domain = device_tracker.DOMAIN
    config = DEFAULT_CONFIG
    await help_test_reloadable(menuai, mqtt_client_mock, domain, config)


@pytest.mark.parametrize(
    "menuai_config",
    [
        help_custom_config(
            device_tracker.DOMAIN,
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
        ("test-topic", "home", "work"),
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
            device_tracker.DOMAIN,
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
