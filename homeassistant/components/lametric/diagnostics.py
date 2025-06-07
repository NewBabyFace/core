"""Diagnostics support for LaMetric."""

from __future__ import annotations

import json
from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.config_entries import ConfigEntry
from menuai.core import menuai

from .const import DOMAIN
from .coordinator import LaMetricDataUpdateCoordinator

TO_REDACT = {
    "device_id",
    "name",
    "serial_number",
    "ssid",
}


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: LaMetricDataUpdateCoordinator = menuai.data[DOMAIN][entry.entry_id]
    # Round-trip via JSON to trigger serialization
    data = json.loads(coordinator.data.to_json())
    return async_redact_data(data, TO_REDACT)
