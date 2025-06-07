"""Diagnostics support for Elgato."""

from __future__ import annotations

from typing import Any

from menuai.core import menuai

from .coordinator import ElgatoConfigEntry


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: ElgatoConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    return {
        "info": coordinator.data.info.to_dict(),
        "state": coordinator.data.state.to_dict(),
    }
