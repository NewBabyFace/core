"""Diagnostics support for Ring."""

from __future__ import annotations

from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.core import menuai

from . import RingConfigEntry

TO_REDACT = {
    "id",
    "device_id",
    "description",
    "first_name",
    "last_name",
    "email",
    "location_id",
    "ring_net_id",
    "wifi_name",
    "latitude",
    "longitude",
    "address",
    "ring_id",
}


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: RingConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    ring_data = entry.runtime_data
    devices_data = ring_data.api.devices_data
    devices_raw = [
        devices_data[device_type][device_id]
        for device_type in devices_data
        for device_id in devices_data[device_type]
    ]
    return async_redact_data(
        {"device_data": devices_raw},
        TO_REDACT,
    )
