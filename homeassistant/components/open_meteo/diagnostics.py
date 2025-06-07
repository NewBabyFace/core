"""Diagnostics support for Open-Meteo."""

from __future__ import annotations

from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.const import CONF_LATITUDE, CONF_LONGITUDE
from menuai.core import menuai

from .coordinator import OpenMeteoConfigEntry

TO_REDACT = {
    CONF_LATITUDE,
    CONF_LONGITUDE,
}


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: OpenMeteoConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    return async_redact_data(coordinator.data.to_dict(), TO_REDACT)
