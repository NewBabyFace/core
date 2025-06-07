"""Diagnostics support for AndroidTV."""

from __future__ import annotations

from typing import Any

import attr

from menuai.components.diagnostics import async_redact_data
from menuai.const import ATTR_CONNECTIONS, ATTR_IDENTIFIERS, CONF_UNIQUE_ID
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er

from . import AndroidTVConfigEntry
from .const import DOMAIN, PROP_ETHMAC, PROP_SERIALNO, PROP_WIFIMAC

TO_REDACT = {CONF_UNIQUE_ID}  # UniqueID contain MAC Address
TO_REDACT_DEV = {ATTR_CONNECTIONS, ATTR_IDENTIFIERS}
TO_REDACT_DEV_PROP = {PROP_ETHMAC, PROP_SERIALNO, PROP_WIFIMAC}


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: AndroidTVConfigEntry
) -> dict[str, dict[str, Any]]:
    """Return diagnostics for a config entry."""
    data = {"entry": async_redact_data(entry.as_dict(), TO_REDACT)}

    # Get information from AndroidTV library
    aftv = entry.runtime_data.aftv
    data["device_properties"] = {
        **async_redact_data(aftv.device_properties, TO_REDACT_DEV_PROP),
        "device_class": aftv.DEVICE_CLASS,
    }

    # Gather information how this AndroidTV device is represented in MenuAI
    device_registry = dr.async_get(menuai)
    entity_registry = er.async_get(menuai)
    menuai_device = device_registry.async_get_device(
        identifiers={(DOMAIN, str(entry.unique_id))}
    )
    if not menuai_device:
        return data

    data["device"] = {
        **async_redact_data(attr.asdict(menuai_device), TO_REDACT_DEV),
        "entities": {},
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

    return data
