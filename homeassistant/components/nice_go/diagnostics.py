"""Diagnostics support for Nice G.O.."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.const import CONF_EMAIL, CONF_PASSWORD
from menuai.core import menuai

from .const import CONF_REFRESH_TOKEN
from .coordinator import NiceGOConfigEntry

TO_REDACT = {CONF_PASSWORD, CONF_EMAIL, CONF_REFRESH_TOKEN, "title", "unique_id"}


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: NiceGOConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data

    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "coordinator_data": {
            device_id: asdict(device_data)
            for device_id, device_data in coordinator.data.items()
        },
    }
