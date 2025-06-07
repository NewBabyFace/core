"""Provides diagnostics for Aussie Broadband."""

from __future__ import annotations

from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.core import menuai

from .coordinator import AussieBroadbandConfigEntry

TO_REDACT = ["address", "ipAddresses", "description", "discounts", "coordinator"]


async def async_get_config_entry_diagnostics(
    menuai: menuai, config_entry: AussieBroadbandConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    return {
        "services": [
            {
                "service": async_redact_data(service, TO_REDACT),
                "usage": async_redact_data(service["coordinator"].data, ["historical"]),
            }
            for service in config_entry.runtime_data
        ]
    }
