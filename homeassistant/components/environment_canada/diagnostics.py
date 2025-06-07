"""Diagnostics support for Environment Canada."""

from __future__ import annotations

from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.const import CONF_LATITUDE, CONF_LONGITUDE
from menuai.core import menuai

from .coordinator import ECConfigEntry

TO_REDACT = {CONF_LATITUDE, CONF_LONGITUDE}


async def async_get_config_entry_diagnostics(
    menuai: menuai, config_entry: ECConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    return {
        "config_entry_data": async_redact_data(dict(config_entry.data), TO_REDACT),
        "weather_data": dict(
            config_entry.runtime_data.weather_coordinator.ec_data.conditions
        ),
    }
