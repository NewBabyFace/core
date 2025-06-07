"""The tests for the MQTT room presence sensor."""

import datetime
import json
from typing import Any
from unittest.mock import patch

import pytest

from menuai.components import sensor
from menuai.components.mqtt import CONF_QOS, CONF_STATE_TOPIC, DEFAULT_QOS
from menuai.const import (
    CONF_DEVICE_ID,
    CONF_NAME,
    CONF_PLATFORM,
    CONF_TIMEOUT,
    CONF_UNIQUE_ID,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import async_fire_mqtt_message
from tests.typing import MqttMockHAClient

DEVICE_ID = "123TESTMAC"
NAME = "test_device"
BEDROOM = "bedroom"
LIVING_ROOM = "living_room"

BEDROOM_TOPIC = f"room_presence/{BEDROOM}"
LIVING_ROOM_TOPIC = f"room_presence/{LIVING_ROOM}"

SENSOR_STATE = f"sensor.{NAME}"

NEAR_MESSAGE = {"id": DEVICE_ID, "name": NAME, "distance": 1}

FAR_MESSAGE = {"id": DEVICE_ID, "name": NAME, "distance": 10}

REALLY_FAR_MESSAGE = {"id": DEVICE_ID, "name": NAME, "distance": 20}


async def send_message(
    menuai: menuai, topic: str, message: dict[str, Any]
) -> None:
    """Test the sending of a message."""
    async_fire_mqtt_message(menuai, topic, json.dumps(message))
    await menuai.async_block_till_done()
    await menuai.async_block_till_done()


async def assert_state(menuai: menuai, room: str) -> None:
    """Test the assertion of a room state."""
    state = menuai.states.get(SENSOR_STATE)
    assert state.state == room


async def assert_distance(menuai: menuai, distance: int) -> None:
    """Test the assertion of a distance state."""
    state = menuai.states.get(SENSOR_STATE)
    assert state.attributes.get("distance") == distance


async def test_no_mqtt(menuai: menuai, caplog: pytest.LogCaptureFixture) -> None:
    """Test no mqtt available."""
    assert await async_setup_component(
        menuai,
        sensor.DOMAIN,
        {
            sensor.DOMAIN: {
                CONF_PLATFORM: "mqtt_room",
                CONF_NAME: NAME,
                CONF_DEVICE_ID: DEVICE_ID,
                CONF_STATE_TOPIC: "room_presence",
                CONF_QOS: DEFAULT_QOS,
                CONF_TIMEOUT: 5,
            }
        },
    )
    await menuai.async_block_till_done()
    state = menuai.states.get(SENSOR_STATE)
    assert state is None
    assert "MQTT integration is not available" in caplog.text


async def test_room_update(menuai: menuai, mqtt_mock: MqttMockHAClient) -> None:
    """Test the updating between rooms."""
    assert await async_setup_component(
        menuai,
        sensor.DOMAIN,
        {
            sensor.DOMAIN: {
                CONF_PLATFORM: "mqtt_room",
                CONF_NAME: NAME,
                CONF_DEVICE_ID: DEVICE_ID,
                CONF_STATE_TOPIC: "room_presence",
                CONF_QOS: DEFAULT_QOS,
                CONF_TIMEOUT: 5,
            }
        },
    )
    await menuai.async_block_till_done()

    await send_message(menuai, BEDROOM_TOPIC, FAR_MESSAGE)
    await assert_state(menuai, BEDROOM)
    await assert_distance(menuai, 10)

    await send_message(menuai, LIVING_ROOM_TOPIC, NEAR_MESSAGE)
    await assert_state(menuai, LIVING_ROOM)
    await assert_distance(menuai, 1)

    await send_message(menuai, BEDROOM_TOPIC, FAR_MESSAGE)
    await assert_state(menuai, LIVING_ROOM)
    await assert_distance(menuai, 1)

    time = dt_util.utcnow() + datetime.timedelta(seconds=7)
    with patch("menuai.helpers.condition.dt_util.utcnow", return_value=time):
        await send_message(menuai, BEDROOM_TOPIC, FAR_MESSAGE)
        await assert_state(menuai, BEDROOM)
        await assert_distance(menuai, 10)


async def test_unique_id_is_set(
    menuai: menuai, entity_registry: er.EntityRegistry, mqtt_mock: MqttMockHAClient
) -> None:
    """Test the updating between rooms."""
    unique_name = "my_unique_name_0123456789"
    assert await async_setup_component(
        menuai,
        sensor.DOMAIN,
        {
            sensor.DOMAIN: {
                CONF_PLATFORM: "mqtt_room",
                CONF_NAME: NAME,
                CONF_DEVICE_ID: DEVICE_ID,
                CONF_STATE_TOPIC: "room_presence",
                CONF_QOS: DEFAULT_QOS,
                CONF_TIMEOUT: 5,
                CONF_UNIQUE_ID: unique_name,
            }
        },
    )
    await menuai.async_block_till_done()
    state = menuai.states.get(SENSOR_STATE)
    assert state.state is not None

    entry = entity_registry.async_get(SENSOR_STATE)
    assert entry.unique_id == unique_name
