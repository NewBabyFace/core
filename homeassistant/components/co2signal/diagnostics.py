"""Diagnostics support for CO2Signal."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.const import CONF_API_KEY
from menuai.core import menuai

from .coordinator import CO2SignalConfigEntry

TO_REDACT = {CONF_API_KEY}


async def async_get_config_entry_diagnostics(
    menuai: menuai, config_entry: CO2SignalConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = config_entry.runtime_data

    return {
        "config_entry": async_redact_data(config_entry.as_dict(), TO_REDACT),
        "data": asdict(coordinator.data),
    }
