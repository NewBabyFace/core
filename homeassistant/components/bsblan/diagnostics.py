"""Diagnostics support for BSBLan."""

from __future__ import annotations

from typing import Any

from menuai.core import menuai

from . import BSBLanConfigEntry


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: BSBLanConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = entry.runtime_data

    return {
        "info": data.info.to_dict(),
        "device": data.device.to_dict(),
        "coordinator_data": {
            "state": data.coordinator.data.state.to_dict(),
            "sensor": data.coordinator.data.sensor.to_dict(),
        },
        "static": data.static.to_dict(),
    }
