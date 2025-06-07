"""The Tasmota integration."""

from __future__ import annotations

import logging

from hatasmota.const import (
    CONF_IP,
    CONF_MAC,
    CONF_MANUFACTURER,
    CONF_MODEL,
    CONF_NAME,
    CONF_SW_VERSION,
)
from hatasmota.models import TasmotaDeviceConfig
from hatasmota.mqtt import TasmotaMQTTClient

from menuai.components import mqtt
from menuai.components.mqtt import (
    async_prepare_subscribe_topics,
    async_subscribe_topics,
    async_unsubscribe_topics,
)
from menuai.config_entries import ConfigEntry
from menuai.core import menuai, callback
from menuai.helpers import device_registry as dr
from menuai.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceRegistry

from . import device_automation, discovery
from .const import (
    CONF_DISCOVERY_PREFIX,
    DATA_REMOVE_DISCOVER_COMPONENT,
    DATA_UNSUB,
    PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Tasmota from a config entry."""
    menuai.data[DATA_UNSUB] = []

    async def _publish(
        topic: str,
        payload: mqtt.PublishPayloadType,
        qos: int | None,
        retain: bool | None,
    ) -> None:
        await mqtt.async_publish(menuai, topic, payload, qos, retain)

    async def _subscribe_topics(sub_state: dict | None, topics: dict) -> dict:
        # Optionally mark message handlers as callback
        for topic in topics.values():
            if "msg_callback" in topic and "event_loop_safe" in topic:
                topic["msg_callback"] = callback(topic["msg_callback"])
        sub_state = async_prepare_subscribe_topics(menuai, sub_state, topics)
        await async_subscribe_topics(menuai, sub_state)
        return sub_state

    async def _unsubscribe_topics(sub_state: dict | None) -> dict:
        return async_unsubscribe_topics(menuai, sub_state)

    tasmota_mqtt = TasmotaMQTTClient(_publish, _subscribe_topics, _unsubscribe_topics)

    device_registry = dr.async_get(menuai)

    async def async_discover_device(config: TasmotaDeviceConfig, mac: str) -> None:
        """Discover and add a Tasmota device."""
        await async_setup_device(
            menuai, mac, config, entry, tasmota_mqtt, device_registry
        )

    await device_automation.async_setup_entry(menuai, entry)
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    discovery_prefix = entry.data[CONF_DISCOVERY_PREFIX]
    await discovery.async_start(
        menuai, discovery_prefix, entry, tasmota_mqtt, async_discover_device
    )

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    # cleanup platforms
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    # disable discovery
    await discovery.async_stop(menuai)

    # cleanup subscriptions
    for unsub in menuai.data[DATA_UNSUB]:
        unsub()
    menuai.data.pop(DATA_REMOVE_DISCOVER_COMPONENT.format("device_automation"))()
    for platform in PLATFORMS:
        menuai.data.pop(DATA_REMOVE_DISCOVER_COMPONENT.format(platform))()

    # detach device triggers
    device_registry = dr.async_get(menuai)
    devices = dr.async_entries_for_config_entry(device_registry, entry.entry_id)
    for device in devices:
        await device_automation.async_remove_automations(menuai, device.id)

    return True


async def _remove_device(
    menuai: menuai,
    config_entry: ConfigEntry,
    mac: str,
    tasmota_mqtt: TasmotaMQTTClient,
    device_registry: DeviceRegistry,
) -> None:
    """Remove a discovered Tasmota device."""
    device = device_registry.async_get_device(
        connections={(CONNECTION_NETWORK_MAC, mac)}
    )

    if device is None or config_entry.entry_id not in device.config_entries:
        return

    _LOGGER.debug("Removing tasmota from device %s", mac)
    device_registry.async_update_device(
        device.id, remove_config_entry_id=config_entry.entry_id
    )


def _update_device(
    menuai: menuai,
    config_entry: ConfigEntry,
    config: TasmotaDeviceConfig,
    device_registry: DeviceRegistry,
) -> None:
    """Add or update device registry."""
    _LOGGER.debug("Adding or updating tasmota device %s", config[CONF_MAC])
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        configuration_url=f"http://{config[CONF_IP]}/",
        connections={(CONNECTION_NETWORK_MAC, config[CONF_MAC])},
        manufacturer=config[CONF_MANUFACTURER],
        model=config[CONF_MODEL],
        name=config[CONF_NAME],
        sw_version=config[CONF_SW_VERSION],
    )


async def async_setup_device(
    menuai: menuai,
    mac: str,
    config: TasmotaDeviceConfig,
    config_entry: ConfigEntry,
    tasmota_mqtt: TasmotaMQTTClient,
    device_registry: DeviceRegistry,
) -> None:
    """Set up the Tasmota device."""
    if not config:
        await _remove_device(menuai, config_entry, mac, tasmota_mqtt, device_registry)
    else:
        _update_device(menuai, config_entry, config, device_registry)


async def async_remove_config_entry_device(
    menuai: menuai, config_entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Remove Tasmota config entry from a device."""

    connections = device_entry.connections
    macs = [c[1] for c in connections if c[0] == CONNECTION_NETWORK_MAC]
    tasmota_discovery = menuai.data[discovery.TASMOTA_DISCOVERY_INSTANCE]
    for mac in macs:
        await tasmota_discovery.clear_discovery_topic(
            mac, config_entry.data[CONF_DISCOVERY_PREFIX]
        )

    return True
