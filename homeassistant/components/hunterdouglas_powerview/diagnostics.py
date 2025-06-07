"""Diagnostics support for Powerview Hunter Douglas."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

import attr

from menuai.components.diagnostics import async_redact_data
from menuai.const import ATTR_CONFIGURATION_URL, CONF_HOST
from menuai.core import menuai, callback
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.helpers.device_registry import DeviceEntry

from .const import REDACT_HUB_ADDRESS, REDACT_MAC_ADDRESS, REDACT_SERIAL_NUMBER
from .model import PowerviewConfigEntry

REDACT_CONFIG = {
    CONF_HOST,
    REDACT_HUB_ADDRESS,
    REDACT_MAC_ADDRESS,
    REDACT_SERIAL_NUMBER,
    ATTR_CONFIGURATION_URL,
}


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: PowerviewConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = _async_get_diagnostics(menuai, entry)
    device_registry = dr.async_get(menuai)
    data.update(
        device_info=[
            _async_device_as_dict(menuai, device)
            for device in dr.async_entries_for_config_entry(
                device_registry, entry.entry_id
            )
        ],
    )
    return data


async def async_get_device_diagnostics(
    menuai: menuai, entry: PowerviewConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    """Return diagnostics for a device entry."""
    data = _async_get_diagnostics(menuai, entry)
    data["device_info"] = _async_device_as_dict(menuai, device)
    # try to match on name to restrict to shade if we can
    # otherwise just return all shade data
    # shade name is unique in powerview
    shade_data = data["shade_data"]
    for shade in shade_data:
        if shade_data[shade]["name_unicode"] == device.name:
            data["shade_data"] = shade_data[shade]
    return data


@callback
def _async_get_diagnostics(
    menuai: menuai,
    entry: PowerviewConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    pv_entry = entry.runtime_data
    shade_data = pv_entry.coordinator.data.get_all_raw_data()
    hub_info = async_redact_data(asdict(pv_entry.device_info), REDACT_CONFIG)
    return {"hub_info": hub_info, "shade_data": shade_data}


@callback
def _async_device_as_dict(menuai: menuai, device: DeviceEntry) -> dict[str, Any]:
    """Represent a Powerview device as a dictionary."""

    # Gather information how this device is represented in MenuAI
    entity_registry = er.async_get(menuai)

    data = async_redact_data(attr.asdict(device), REDACT_CONFIG)
    data["entities"] = []
    entities: list[dict[str, Any]] = data["entities"]

    entries = er.async_entries_for_device(
        entity_registry,
        device_id=device.id,
        include_disabled_entities=True,
    )

    for entity_entry in entries:
        state = menuai.states.get(entity_entry.entity_id)
        state_dict = None
        if state:
            state_dict = dict(state.as_dict())
            state_dict.pop("context", None)

        entity = attr.asdict(entity_entry)
        entity["state"] = state_dict
        entities.append(entity)

    return data
