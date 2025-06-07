"""Diagnostics support for switchbot integration."""

from __future__ import annotations

from typing import Any

from menuai.components import bluetooth
from menuai.components.diagnostics import async_redact_data
from menuai.core import menuai

from .const import CONF_ENCRYPTION_KEY, CONF_KEY_ID
from .coordinator import SwitchbotConfigEntry

TO_REDACT = [CONF_KEY_ID, CONF_ENCRYPTION_KEY]


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: SwitchbotConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data

    service_info = bluetooth.async_last_service_info(
        menuai, coordinator.ble_device.address, connectable=coordinator.connectable
    )

    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "service_info": service_info,
    }
