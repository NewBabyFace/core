"""Diagnostics support for pegel_online."""

from __future__ import annotations

from typing import Any

from menuai.core import menuai

from .coordinator import PegelOnlineConfigEntry


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: PegelOnlineConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data

    return {
        "entry": entry.as_dict(),
        "data": coordinator.data,
    }
