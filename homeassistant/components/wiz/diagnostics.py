"""Diagnostics support for WiZ."""

from __future__ import annotations

from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.core import menuai

from . import WizConfigEntry

TO_REDACT = {"roomId", "homeId"}


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: WizConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    return {
        "entry": {
            "title": entry.title,
            "data": dict(entry.data),
        },
        "data": async_redact_data(entry.runtime_data.bulb.diagnostics, TO_REDACT),
    }
