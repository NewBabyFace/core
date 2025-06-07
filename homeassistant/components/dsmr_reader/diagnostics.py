"""Diagnostics support for DSMR Reader."""

from __future__ import annotations

from typing import Any

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers import entity_registry as er


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for the config entry."""
    ent_reg = er.async_get(menuai)
    entities = [
        entity.entity_id
        for entity in er.async_entries_for_config_entry(ent_reg, entry.entry_id)
    ]

    entity_states = {entity: menuai.states.get(entity) for entity in entities}

    return {
        "entry": entry.as_dict(),
        "entities": entity_states,
    }
