"""Diagnostics support for GIOS."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from menuai.core import menuai

from .coordinator import GiosConfigEntry


async def async_get_config_entry_diagnostics(
    menuai: menuai, config_entry: GiosConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = config_entry.runtime_data.coordinator

    return {
        "config_entry": config_entry.as_dict(),
        "coordinator_data": asdict(coordinator.data),
    }
