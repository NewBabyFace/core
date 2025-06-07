"""Diagnostics support for SMA."""

from __future__ import annotations

from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_PASSWORD
from menuai.core import menuai
from menuai.helpers import entity_registry as er

TO_REDACT = {CONF_PASSWORD}


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

    entry_dict = entry.as_dict()
    if "data" in entry_dict:
        entry_dict["data"] = async_redact_data(entry_dict["data"], TO_REDACT)

    return {
        "entry": entry_dict,
        "entities": entity_states,
    }
