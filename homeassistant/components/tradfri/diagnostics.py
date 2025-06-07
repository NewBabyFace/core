"""Diagnostics support for IKEA Tradfri."""

from __future__ import annotations

from typing import Any, cast

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from .const import CONF_GATEWAY_ID, COORDINATOR, COORDINATOR_LIST, DOMAIN


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics the Tradfri platform."""
    entry_data = menuai.data[DOMAIN][entry.entry_id]
    coordinator_data = entry_data[COORDINATOR]

    device_registry = dr.async_get(menuai)
    device = cast(
        dr.DeviceEntry,
        device_registry.async_get_device(
            identifiers={(DOMAIN, entry.data[CONF_GATEWAY_ID])}
        ),
    )

    device_data: list = [
        coordinator.device.device_info.model_number
        for coordinator in coordinator_data[COORDINATOR_LIST]
    ]

    return {
        "gateway_version": device.sw_version,
        "device_data": sorted(device_data),
    }
