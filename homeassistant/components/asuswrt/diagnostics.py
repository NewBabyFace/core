"""Diagnostics support for Asuswrt."""

from __future__ import annotations

from typing import Any

import attr

from menuai.components.diagnostics import async_redact_data
from menuai.const import (
    ATTR_CONNECTIONS,
    ATTR_IDENTIFIERS,
    CONF_PASSWORD,
    CONF_UNIQUE_ID,
    CONF_USERNAME,
)
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er

from . import AsusWrtConfigEntry

TO_REDACT = {CONF_PASSWORD, CONF_UNIQUE_ID, CONF_USERNAME}
TO_REDACT_DEV = {ATTR_CONNECTIONS, ATTR_IDENTIFIERS}


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: AsusWrtConfigEntry
) -> dict[str, dict[str, Any]]:
    """Return diagnostics for a config entry."""
    data = {"entry": async_redact_data(entry.as_dict(), TO_REDACT)}

    router = entry.runtime_data

    # Gather information how this AsusWrt device is represented in MenuAI
    device_registry = dr.async_get(menuai)
    entity_registry = er.async_get(menuai)
    menuai_device = device_registry.async_get_device(
        identifiers=router.device_info[ATTR_IDENTIFIERS]
    )
    if not menuai_device:
        return data

    data["device"] = {
        **async_redact_data(attr.asdict(menuai_device), TO_REDACT_DEV),
        "entities": {},
        "tracked_devices": [],
    }

    menuai_entities = er.async_entries_for_device(
        entity_registry,
        device_id=menuai_device.id,
        include_disabled_entities=True,
    )

    for entity_entry in menuai_entities:
        state = menuai.states.get(entity_entry.entity_id)
        state_dict = None
        if state:
            state_dict = dict(state.as_dict())
            # The entity_id is already provided at root level.
            state_dict.pop("entity_id", None)
            # The context doesn't provide useful information in this case.
            state_dict.pop("context", None)

        data["device"]["entities"][entity_entry.entity_id] = {
            **async_redact_data(
                attr.asdict(
                    entity_entry, filter=lambda attr, value: attr.name != "entity_id"
                ),
                TO_REDACT,
            ),
            "state": state_dict,
        }

    for device in router.devices.values():
        data["device"]["tracked_devices"].append(
            {
                "name": device.name or "Unknown device",
                "ip_address": device.ip_address,
                "last_activity": device.last_activity,
            }
        )

    return data
