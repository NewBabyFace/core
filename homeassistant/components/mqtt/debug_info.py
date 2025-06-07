"""Helper to handle a set of topics to subscribe to."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import datetime as dt
import time
from typing import TYPE_CHECKING, Any

from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.helpers.typing import DiscoveryInfoType
from menuai.util import dt as dt_util

from .const import ATTR_DISCOVERY_PAYLOAD, ATTR_DISCOVERY_TOPIC
from .models import DATA_MQTT, PublishPayloadType

STORED_MESSAGES = 10


@dataclass
class TimestampedPublishMessage:
    """MQTT Message."""

    topic: str
    payload: PublishPayloadType
    qos: int
    retain: bool
    timestamp: float


def log_message(
    menuai: menuai,
    entity_id: str,
    topic: str,
    payload: PublishPayloadType,
    qos: int,
    retain: bool,
) -> None:
    """Log an outgoing MQTT message."""
    entity_info = menuai.data[DATA_MQTT].debug_info_entities.setdefault(
        entity_id, {"subscriptions": {}, "discovery_data": {}, "transmitted": {}}
    )
    if topic not in entity_info["transmitted"]:
        entity_info["transmitted"][topic] = {
            "messages": deque([], STORED_MESSAGES),
        }
    msg = TimestampedPublishMessage(
        topic, payload, qos, retain, timestamp=time.monotonic()
    )
    entity_info["transmitted"][topic]["messages"].append(msg)


def add_subscription(
    menuai: menuai, subscription: str, entity_id: str | None
) -> None:
    """Prepare debug data for subscription."""
    if entity_id:
        entity_info = menuai.data[DATA_MQTT].debug_info_entities.setdefault(
            entity_id, {"subscriptions": {}, "discovery_data": {}, "transmitted": {}}
        )
        if subscription not in entity_info["subscriptions"]:
            entity_info["subscriptions"][subscription] = {
                "count": 1,
                "messages": deque([], STORED_MESSAGES),
            }
        else:
            entity_info["subscriptions"][subscription]["count"] += 1


def remove_subscription(
    menuai: menuai, subscription: str, entity_id: str | None
) -> None:
    """Remove debug data for subscription if it exists."""
    if entity_id and entity_id in (
        debug_info_entities := menuai.data[DATA_MQTT].debug_info_entities
    ):
        subscriptions = debug_info_entities[entity_id]["subscriptions"]
        subscriptions[subscription]["count"] -= 1
        if not subscriptions[subscription]["count"]:
            del subscriptions[subscription]


def add_entity_discovery_data(
    menuai: menuai, discovery_data: DiscoveryInfoType, entity_id: str
) -> None:
    """Add discovery data."""
    entity_info = menuai.data[DATA_MQTT].debug_info_entities.setdefault(
        entity_id, {"subscriptions": {}, "discovery_data": {}, "transmitted": {}}
    )
    entity_info["discovery_data"] = discovery_data


def update_entity_discovery_data(
    menuai: menuai, discovery_payload: DiscoveryInfoType, entity_id: str
) -> None:
    """Update discovery data."""
    discovery_data = menuai.data[DATA_MQTT].debug_info_entities[entity_id][
        "discovery_data"
    ]
    if TYPE_CHECKING:
        assert discovery_data is not None
    discovery_data[ATTR_DISCOVERY_PAYLOAD] = discovery_payload


def remove_entity_data(menuai: menuai, entity_id: str) -> None:
    """Remove discovery data."""
    if entity_id in (debug_info_entities := menuai.data[DATA_MQTT].debug_info_entities):
        del debug_info_entities[entity_id]


def add_trigger_discovery_data(
    menuai: menuai,
    discovery_hash: tuple[str, str],
    discovery_data: DiscoveryInfoType,
    device_id: str,
) -> None:
    """Add discovery data."""
    menuai.data[DATA_MQTT].debug_info_triggers[discovery_hash] = {
        "device_id": device_id,
        "discovery_data": discovery_data,
    }


def update_trigger_discovery_data(
    menuai: menuai,
    discovery_hash: tuple[str, str],
    discovery_payload: DiscoveryInfoType,
) -> None:
    """Update discovery data."""
    menuai.data[DATA_MQTT].debug_info_triggers[discovery_hash]["discovery_data"][
        ATTR_DISCOVERY_PAYLOAD
    ] = discovery_payload


def remove_trigger_discovery_data(
    menuai: menuai, discovery_hash: tuple[str, str]
) -> None:
    """Remove discovery data."""
    menuai.data[DATA_MQTT].debug_info_triggers.pop(discovery_hash, None)


def _info_for_entity(menuai: menuai, entity_id: str) -> dict[str, Any]:
    entity_info = menuai.data[DATA_MQTT].debug_info_entities[entity_id]
    monotonic_time_diff = time.time() - time.monotonic()
    subscriptions = [
        {
            "topic": topic,
            "messages": [
                {
                    "payload": str(msg.payload),
                    "qos": msg.qos,
                    "retain": msg.retain,
                    "time": dt_util.utc_from_timestamp(
                        msg.timestamp + monotonic_time_diff,
                        tz=dt.UTC,
                    ),
                    "topic": msg.topic,
                }
                for msg in subscription["messages"]
            ],
        }
        for topic, subscription in entity_info["subscriptions"].items()
    ]
    transmitted = [
        {
            "topic": topic,
            "messages": [
                {
                    "payload": str(msg.payload),
                    "qos": msg.qos,
                    "retain": msg.retain,
                    "time": dt_util.utc_from_timestamp(
                        msg.timestamp + monotonic_time_diff,
                        tz=dt.UTC,
                    ),
                    "topic": msg.topic,
                }
                for msg in subscription["messages"]
            ],
        }
        for topic, subscription in entity_info["transmitted"].items()
    ]
    discovery_data = {
        "topic": entity_info["discovery_data"].get(ATTR_DISCOVERY_TOPIC, ""),
        "payload": entity_info["discovery_data"].get(ATTR_DISCOVERY_PAYLOAD, ""),
    }

    return {
        "entity_id": entity_id,
        "subscriptions": subscriptions,
        "discovery_data": discovery_data,
        "transmitted": transmitted,
    }


def _info_for_trigger(
    menuai: menuai, trigger_key: tuple[str, str]
) -> dict[str, Any]:
    trigger = menuai.data[DATA_MQTT].debug_info_triggers[trigger_key]
    discovery_data = None
    if trigger["discovery_data"] is not None:
        discovery_data = {
            "topic": trigger["discovery_data"][ATTR_DISCOVERY_TOPIC],
            "payload": trigger["discovery_data"][ATTR_DISCOVERY_PAYLOAD],
        }
    return {"discovery_data": discovery_data, "trigger_key": trigger_key}


def info_for_config_entry(menuai: menuai) -> dict[str, list[Any]]:
    """Get debug info for all entities and triggers."""

    mqtt_data = menuai.data[DATA_MQTT]
    mqtt_info: dict[str, list[Any]] = {"entities": [], "triggers": []}

    mqtt_info["entities"].extend(
        _info_for_entity(menuai, entity_id) for entity_id in mqtt_data.debug_info_entities
    )

    mqtt_info["triggers"].extend(
        _info_for_trigger(menuai, trigger_key)
        for trigger_key in mqtt_data.debug_info_triggers
    )

    return mqtt_info


def info_for_device(menuai: menuai, device_id: str) -> dict[str, list[Any]]:
    """Get debug info for a device."""

    mqtt_data = menuai.data[DATA_MQTT]

    mqtt_info: dict[str, list[Any]] = {"entities": [], "triggers": []}
    entity_registry = er.async_get(menuai)

    entries = er.async_entries_for_device(
        entity_registry, device_id, include_disabled_entities=True
    )
    mqtt_info["entities"].extend(
        _info_for_entity(menuai, entry.entity_id)
        for entry in entries
        if entry.entity_id in mqtt_data.debug_info_entities
    )

    mqtt_info["triggers"].extend(
        _info_for_trigger(menuai, trigger_key)
        for trigger_key, trigger in mqtt_data.debug_info_triggers.items()
        if trigger["device_id"] == device_id
    )

    return mqtt_info
