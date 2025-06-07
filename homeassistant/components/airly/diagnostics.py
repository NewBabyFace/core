"""Diagnostics support for Airly."""

from __future__ import annotations

from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_UNIQUE_ID,
)
from menuai.core import menuai

from .coordinator import AirlyConfigEntry

TO_REDACT = {CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE, CONF_UNIQUE_ID}


async def async_get_config_entry_diagnostics(
    menuai: menuai, config_entry: AirlyConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = config_entry.runtime_data

    return {
        "config_entry": async_redact_data(config_entry.as_dict(), TO_REDACT),
        "coordinator_data": coordinator.data,
    }
