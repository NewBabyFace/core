"""Diagnostics support for IMGW-PIB."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from menuai.core import menuai

from .coordinator import ImgwPibConfigEntry


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: ImgwPibConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data.coordinator

    return {
        "config_entry_data": entry.as_dict(),
        "hydrological_data": asdict(coordinator.data),
    }
