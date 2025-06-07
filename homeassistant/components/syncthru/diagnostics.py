"""Diagnostics support for Syncthru."""

from __future__ import annotations

from typing import Any

from menuai.core import menuai

from .coordinator import SyncThruConfigEntry


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: SyncThruConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    return entry.runtime_data.data.raw()
