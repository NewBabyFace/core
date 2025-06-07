"""Diagnostics support for Pure Energie."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.const import CONF_HOST
from menuai.core import menuai

from .coordinator import PureEnergieConfigEntry

TO_REDACT = {
    CONF_HOST,
    "n2g_id",
}


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: PureEnergieConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    return {
        "entry": {
            "title": entry.title,
            "data": async_redact_data(entry.data, TO_REDACT),
        },
        "data": {
            "device": async_redact_data(
                asdict(entry.runtime_data.data.device), TO_REDACT
            ),
            "smartbridge": asdict(entry.runtime_data.data.smartbridge),
        },
    }
