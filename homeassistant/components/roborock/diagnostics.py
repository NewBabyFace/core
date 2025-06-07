"""Support for the Airzone diagnostics."""

from __future__ import annotations

from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.const import CONF_UNIQUE_ID
from menuai.core import menuai

from .coordinator import RoborockConfigEntry

TO_REDACT_CONFIG = ["token", "sn", "rruid", CONF_UNIQUE_ID, "username", "uid"]

TO_REDACT_COORD = ["duid", "localKey", "mac", "bssid"]


async def async_get_config_entry_diagnostics(
    menuai: menuai, config_entry: RoborockConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinators = config_entry.runtime_data

    return {
        "config_entry": async_redact_data(config_entry.data, TO_REDACT_CONFIG),
        "coordinators": {
            f"**REDACTED-{i}**": {
                "roborock_device_info": async_redact_data(
                    coordinator.roborock_device_info.as_dict(), TO_REDACT_COORD
                ),
                "api": coordinator.api.diagnostic_data,
            }
            for i, coordinator in enumerate(coordinators.values())
        },
    }
