"""Diagnostics support for DSMR."""

from __future__ import annotations

from typing import Any

from menuai.core import menuai
from menuai.util.json import json_loads

from . import DsmrConfigEntry


async def async_get_config_entry_diagnostics(
    menuai: menuai, config_entry: DsmrConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    return {
        "entry": {
            "data": {
                **config_entry.data,
            },
            "unique_id": config_entry.unique_id,
        },
        "data": json_loads(config_entry.runtime_data.telegram.to_json())
        if config_entry.runtime_data.telegram
        else None,
    }
