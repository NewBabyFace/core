"""Diagnostics support for Roku."""

from __future__ import annotations

from typing import Any

from menuai.core import menuai

from .coordinator import RokuConfigEntry


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: RokuConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    return {
        "entry": {
            "data": {
                **entry.data,
            },
            "unique_id": entry.unique_id,
        },
        "data": entry.runtime_data.data.as_dict(),
    }
