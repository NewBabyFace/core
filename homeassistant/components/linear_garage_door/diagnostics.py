"""Diagnostics support for Linear Garage Door."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_EMAIL, CONF_PASSWORD
from menuai.core import menuai

from .const import DOMAIN
from .coordinator import LinearUpdateCoordinator

TO_REDACT = {CONF_PASSWORD, CONF_EMAIL}


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: LinearUpdateCoordinator = menuai.data[DOMAIN][entry.entry_id]

    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "coordinator_data": {
            device_id: asdict(device_data)
            for device_id, device_data in coordinator.data.items()
        },
    }
