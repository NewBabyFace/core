"""Diagnostics support for MQTT."""

from __future__ import annotations

from typing import Any

from menuai.components import device_tracker
from menuai.components.diagnostics import async_redact_data
from menuai.config_entries import ConfigEntry
from menuai.const import (
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from menuai.core import menuai, callback, split_entity_id
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.helpers.device_registry import DeviceEntry

from . import debug_info, is_connected

REDACT_CONFIG = {CONF_PASSWORD, CONF_USERNAME}
REDACT_STATE_DEVICE_TRACKER = {ATTR_LATITUDE, ATTR_LONGITUDE}


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    return _async_get_diagnostics(menuai, entry)


async def async_get_device_diagnostics(
    menuai: menuai, entry: ConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    """Return diagnostics for a device entry."""
    return _async_get_diagnostics(menuai, entry, device)


@callback
def _async_get_diagnostics(
    menuai: menuai,
    entry: ConfigEntry,
    device: DeviceEntry | None = None,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    redacted_config = {
        "data": async_redact_data(dict(entry.data), REDACT_CONFIG),
        "options": dict(entry.options),
    }

    data = {
        "connected": is_connected(menuai),
        "mqtt_config": redacted_config,
    }

    if device:
        data["device"] = _async_device_as_dict(menuai, device)
        data["mqtt_debug_info"] = debug_info.info_for_device(menuai, device.id)
    else:
        device_registry = dr.async_get(menuai)
        data.update(
            devices=[
                _async_device_as_dict(menuai, device)
                for device in dr.async_entries_for_config_entry(
                    device_registry, entry.entry_id
                )
            ],
            mqtt_debug_info=debug_info.info_for_config_entry(menuai),
        )

    return data


@callback
def _async_device_as_dict(menuai: menuai, device: DeviceEntry) -> dict[str, Any]:
    """Represent an MQTT device as a dictionary."""

    # Gather information how this MQTT device is represented in MenuAI
    entity_registry = er.async_get(menuai)
    data: dict[str, Any] = {
        "id": device.id,
        "name": device.name,
        "name_by_user": device.name_by_user,
        "disabled": device.disabled,
        "disabled_by": device.disabled_by,
        "entities": [],
    }

    entities = er.async_entries_for_device(
        entity_registry,
        device_id=device.id,
        include_disabled_entities=True,
    )

    def _state_dict(entity_entry: er.RegistryEntry) -> dict[str, Any] | None:
        state = menuai.states.get(entity_entry.entity_id)
        if not state:
            return None

        state_dict = dict(state.as_dict())

        # The context doesn't provide useful information in this case.
        state_dict.pop("context", None)

        entity_domain = split_entity_id(state.entity_id)[0]

        # Retract some sensitive state attributes
        if entity_domain == device_tracker.DOMAIN:
            state_dict["attributes"] = async_redact_data(
                state_dict["attributes"], REDACT_STATE_DEVICE_TRACKER
            )
        return state_dict

    data["entities"].extend(
        {
            "device_class": entity_entry.device_class,
            "disabled_by": entity_entry.disabled_by,
            "disabled": entity_entry.disabled,
            "entity_category": entity_entry.entity_category,
            "entity_id": entity_entry.entity_id,
            "icon": entity_entry.icon,
            "original_device_class": entity_entry.original_device_class,
            "original_icon": entity_entry.original_icon,
            "state": state_dict,
            "unit_of_measurement": entity_entry.unit_of_measurement,
        }
        for entity_entry in entities
        if (state_dict := _state_dict(entity_entry)) is not None
    )

    return data
