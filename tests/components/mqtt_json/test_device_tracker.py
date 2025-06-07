"""The tests for the JSON MQTT device tracker platform."""

from collections.abc import AsyncGenerator
import json
import logging
import os
from unittest.mock import patch

import pytest

from menuai.components.device_tracker.legacy import (
    DOMAIN as DT_DOMAIN,
    YAML_DEVICES,
    AsyncSeeCallback,
)
from menuai.components.mqtt import DOMAIN as MQTT_DOMAIN
from menuai.config_entries import ConfigEntryDisabler
from menuai.const import CONF_PLATFORM
from menuai.core import menuai
from menuai.helpers.typing import ConfigType, DiscoveryInfoType
from menuai.setup import async_setup_component

from tests.common import async_fire_mqtt_message
from tests.typing import MqttMockHAClient

LOCATION_MESSAGE = {
    "longitude": 1.0,
    "gps_accuracy": 60,
    "latitude": 2.0,
    "battery_level": 99.9,
}

LOCATION_MESSAGE_INCOMPLETE = {"longitude": 2.0}


@pytest.fixture(autouse=True)
async def setup_comp(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> AsyncGenerator[None]:
    """Initialize components."""
    yaml_devices = menuai.config.path(YAML_DEVICES)
    yield
    if os.path.isfile(yaml_devices):
        os.remove(yaml_devices)


async def test_setup_fails_without_mqtt_being_setup(
    menuai: menuai, mqtt_mock: MqttMockHAClient, caplog: pytest.LogCaptureFixture
) -> None:
    """Ensure mqtt is started when we setup the component."""
    # Simulate MQTT is was removed
    mqtt_entry = menuai.config_entries.async_entries(MQTT_DOMAIN)[0]
    await menuai.config_entries.async_unload(mqtt_entry.entry_id)
    await menuai.config_entries.async_set_disabled_by(
        mqtt_entry.entry_id, ConfigEntryDisabler.USER
    )
    # mqtt is mocked so we need to simulate it is not connected
    mqtt_mock.connected = False

    dev_id = "zanzito"
    topic = "location/zanzito"

    await async_setup_component(
        menuai,
        DT_DOMAIN,
        {DT_DOMAIN: {CONF_PLATFORM: "mqtt_json", "devices": {dev_id: topic}}},
    )
    await menuai.async_block_till_done()

    assert "MQTT integration is not available" in caplog.text


async def test_ensure_device_tracker_platform_validation(menuai: menuai) -> None:
    """Test if platform validation was done."""

    async def mock_setup_scanner(
        menuai: menuai,
        config: ConfigType,
        see: AsyncSeeCallback,
        discovery_info: DiscoveryInfoType | None = None,
    ) -> bool:
        """Check that Qos was added by validation."""
        assert "qos" in config
        return True

    with patch(
        "menuai.components.mqtt_json.device_tracker.async_setup_scanner",
        autospec=True,
        side_effect=mock_setup_scanner,
    ) as mock_sp:
        dev_id = "paulus"
        topic = "location/paulus"
        assert await async_setup_component(
            menuai,
            DT_DOMAIN,
            {DT_DOMAIN: {CONF_PLATFORM: "mqtt_json", "devices": {dev_id: topic}}},
        )
        await menuai.async_block_till_done()
        assert mock_sp.call_count == 1


async def test_json_message(menuai: menuai) -> None:
    """Test json location message."""
    dev_id = "zanzito"
    topic = "location/zanzito"
    location = json.dumps(LOCATION_MESSAGE)

    assert await async_setup_component(
        menuai,
        DT_DOMAIN,
        {DT_DOMAIN: {CONF_PLATFORM: "mqtt_json", "devices": {dev_id: topic}}},
    )
    await menuai.async_block_till_done()
    async_fire_mqtt_message(menuai, topic, location)
    await menuai.async_block_till_done()
    state = menuai.states.get("device_tracker.zanzito")
    assert state.attributes.get("latitude") == 2.0
    assert state.attributes.get("longitude") == 1.0


async def test_non_json_message(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test receiving a non JSON message."""
    dev_id = "zanzito"
    topic = "location/zanzito"
    location = "home"

    assert await async_setup_component(
        menuai,
        DT_DOMAIN,
        {DT_DOMAIN: {CONF_PLATFORM: "mqtt_json", "devices": {dev_id: topic}}},
    )
    await menuai.async_block_till_done()

    caplog.set_level(logging.ERROR)
    caplog.clear()
    async_fire_mqtt_message(menuai, topic, location)
    await menuai.async_block_till_done()
    assert "Error parsing JSON payload: home" in caplog.text


async def test_incomplete_message(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test receiving an incomplete message."""
    dev_id = "zanzito"
    topic = "location/zanzito"
    location = json.dumps(LOCATION_MESSAGE_INCOMPLETE)

    assert await async_setup_component(
        menuai,
        DT_DOMAIN,
        {DT_DOMAIN: {CONF_PLATFORM: "mqtt_json", "devices": {dev_id: topic}}},
    )
    await menuai.async_block_till_done()

    caplog.set_level(logging.ERROR)
    caplog.clear()
    async_fire_mqtt_message(menuai, topic, location)
    await menuai.async_block_till_done()
    assert (
        "Skipping update for following data because of missing "
        'or malformatted data: {"longitude": 2.0}' in caplog.text
    )


async def test_single_level_wildcard_topic(menuai: menuai) -> None:
    """Test single level wildcard topic."""
    dev_id = "zanzito"
    subscription = "location/+/zanzito"
    topic = "location/room/zanzito"
    location = json.dumps(LOCATION_MESSAGE)

    assert await async_setup_component(
        menuai,
        DT_DOMAIN,
        {DT_DOMAIN: {CONF_PLATFORM: "mqtt_json", "devices": {dev_id: subscription}}},
    )
    await menuai.async_block_till_done()

    async_fire_mqtt_message(menuai, topic, location)
    await menuai.async_block_till_done()
    state = menuai.states.get("device_tracker.zanzito")
    assert state.attributes.get("latitude") == 2.0
    assert state.attributes.get("longitude") == 1.0


async def test_multi_level_wildcard_topic(menuai: menuai) -> None:
    """Test multi level wildcard topic."""
    dev_id = "zanzito"
    subscription = "location/#"
    topic = "location/zanzito"
    location = json.dumps(LOCATION_MESSAGE)

    assert await async_setup_component(
        menuai,
        DT_DOMAIN,
        {DT_DOMAIN: {CONF_PLATFORM: "mqtt_json", "devices": {dev_id: subscription}}},
    )
    await menuai.async_block_till_done()

    async_fire_mqtt_message(menuai, topic, location)
    await menuai.async_block_till_done()
    state = menuai.states.get("device_tracker.zanzito")
    assert state.attributes.get("latitude") == 2.0
    assert state.attributes.get("longitude") == 1.0


async def test_single_level_wildcard_topic_not_matching(menuai: menuai) -> None:
    """Test not matching single level wildcard topic."""
    dev_id = "zanzito"
    entity_id = f"{DT_DOMAIN}.{dev_id}"
    subscription = "location/+/zanzito"
    topic = "location/zanzito"
    location = json.dumps(LOCATION_MESSAGE)

    assert await async_setup_component(
        menuai,
        DT_DOMAIN,
        {DT_DOMAIN: {CONF_PLATFORM: "mqtt_json", "devices": {dev_id: subscription}}},
    )
    await menuai.async_block_till_done()

    async_fire_mqtt_message(menuai, topic, location)
    await menuai.async_block_till_done()
    assert menuai.states.get(entity_id) is None


async def test_multi_level_wildcard_topic_not_matching(menuai: menuai) -> None:
    """Test not matching multi level wildcard topic."""
    dev_id = "zanzito"
    entity_id = f"{DT_DOMAIN}.{dev_id}"
    subscription = "location/#"
    topic = "somewhere/zanzito"
    location = json.dumps(LOCATION_MESSAGE)

    assert await async_setup_component(
        menuai,
        DT_DOMAIN,
        {DT_DOMAIN: {CONF_PLATFORM: "mqtt_json", "devices": {dev_id: subscription}}},
    )
    await menuai.async_block_till_done()

    async_fire_mqtt_message(menuai, topic, location)
    await menuai.async_block_till_done()
    assert menuai.states.get(entity_id) is None
