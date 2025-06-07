"""Diagnostics support for Nut."""

from __future__ import annotations

from typing import Any

import attr

from menuai.components.diagnostics import async_redact_data
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er

from . import NutConfigEntry
from .const import DOMAIN

TO_REDACT = {CONF_PASSWORD, CONF_USERNAME}


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: NutConfigEntry
) -> dict[str, dict[str, Any]]:
    """Return diagnostics for a config entry."""
    data = {"entry": async_redact_data(entry.as_dict(), TO_REDACT)}
    menuai_data = entry.runtime_data

    # Get information from Nut library
    nut_data = menuai_data.data
    nut_cmd = menuai_data.user_available_commands
    data["nut_data"] = {
        "ups_list": nut_data.ups_list,
        "status": nut_data.status,
        "commands": nut_cmd,
    }

    # Gather information how this Nut device is represented in MenuAI
    device_registry = dr.async_get(menuai)
    entity_registry = er.async_get(menuai)
    menuai_device = device_registry.async_get_device(
        identifiers={(DOMAIN, menuai_data.unique_id)}
    )
    # Device is always created
    assert menuai_device is not None

    data["device"] = {
        **attr.asdict(menuai_device),
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
            **attr.asdict(
                entity_entry, filter=lambda attr, value: attr.name != "entity_id"
            ),
            "state": state_dict,
        }

    return data
