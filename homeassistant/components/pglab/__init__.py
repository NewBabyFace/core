"""PG LAB Electronics integration."""

from __future__ import annotations

from pypglab.mqtt import (
    Client as PyPGLabMqttClient,
    Sub_State as PyPGLabSubState,
    Subscribe_CallBack as PyPGLabSubscribeCallBack,
)

from menuai.components import mqtt
from menuai.components.mqtt import (
    ReceiveMessage,
    async_prepare_subscribe_topics,
    async_subscribe_topics,
    async_unsubscribe_topics,
)
from menuai.config_entries import ConfigEntry
from menuai.core import menuai, callback
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers import config_validation as cv

from .const import DOMAIN, LOGGER
from .discovery import PGLabDiscovery

type PGLabConfigEntry = ConfigEntry[PGLabDiscovery]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup_entry(
    menuai: menuai, config_entry: PGLabConfigEntry
) -> bool:
    """Set up PG LAB Electronics integration from a config entry."""

    async def mqtt_publish(topic: str, payload: str, qos: int, retain: bool) -> None:
        """Publish an MQTT message using the MenuAI MQTT client."""
        await mqtt.async_publish(menuai, topic, payload, qos, retain)

    async def mqtt_subscribe(
        sub_state: PyPGLabSubState, topic: str, callback_func: PyPGLabSubscribeCallBack
    ) -> PyPGLabSubState:
        """Subscribe to MQTT topics using the MenuAI MQTT client."""

        @callback
        def mqtt_message_received(msg: ReceiveMessage) -> None:
            """Handle PGLab mqtt messages."""
            callback_func(msg.topic, msg.payload)

        topics = {
            "pglab_subscribe_topic": {
                "topic": topic,
                "msg_callback": mqtt_message_received,
            }
        }

        sub_state = async_prepare_subscribe_topics(menuai, sub_state, topics)
        await async_subscribe_topics(menuai, sub_state)
        return sub_state

    async def mqtt_unsubscribe(sub_state: PyPGLabSubState) -> None:
        async_unsubscribe_topics(menuai, sub_state)

    if not await mqtt.async_wait_for_mqtt_client(menuai):
        LOGGER.error("MQTT integration not available")
        raise ConfigEntryNotReady("MQTT integration not available")

    # Create an MQTT client for PGLab used for PGLab python module.
    pglab_mqtt = PyPGLabMqttClient(mqtt_publish, mqtt_subscribe, mqtt_unsubscribe)

    # Setup PGLab device discovery.
    config_entry.runtime_data = PGLabDiscovery()

    # Start to discovery PG Lab devices.
    await config_entry.runtime_data.start(menuai, pglab_mqtt, config_entry)

    return True


async def async_unload_entry(
    menuai: menuai, config_entry: PGLabConfigEntry
) -> bool:
    """Unload a config entry."""

    # Stop PGLab device discovery.
    pglab_discovery = config_entry.runtime_data
    await pglab_discovery.stop(menuai, config_entry)

    return True
