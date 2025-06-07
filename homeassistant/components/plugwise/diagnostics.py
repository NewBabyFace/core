"""Diagnostics support for Plugwise."""

from __future__ import annotations

from typing import Any

from menuai.core import menuai

from .coordinator import PlugwiseConfigEntry


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: PlugwiseConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    return coordinator.data
