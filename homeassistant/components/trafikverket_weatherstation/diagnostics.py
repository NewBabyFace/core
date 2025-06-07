"""Diagnostics support for Trafikverket Weatherstation."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from menuai.core import menuai

from . import TVWeatherConfigEntry


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: TVWeatherConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for Trafikverket Weatherstation config entry."""
    return asdict(entry.runtime_data.data)
