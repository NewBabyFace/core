"""Diagnostics support for Devialet."""

from __future__ import annotations

from typing import Any

from menuai.core import menuai

from .coordinator import DevialetConfigEntry


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: DevialetConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    return await entry.runtime_data.client.async_get_diagnostics()
