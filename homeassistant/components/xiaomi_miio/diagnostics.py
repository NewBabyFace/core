"""Diagnostics support for Xiaomi Miio."""

from __future__ import annotations

from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.const import CONF_DEVICE, CONF_MAC, CONF_TOKEN, CONF_UNIQUE_ID
from menuai.core import menuai

from .const import CONF_CLOUD_PASSWORD, CONF_CLOUD_USERNAME, CONF_FLOW_TYPE
from .typing import XiaomiMiioConfigEntry

TO_REDACT = {
    CONF_CLOUD_PASSWORD,
    CONF_CLOUD_USERNAME,
    CONF_MAC,
    CONF_TOKEN,
    CONF_UNIQUE_ID,
}


async def async_get_config_entry_diagnostics(
    menuai: menuai, config_entry: XiaomiMiioConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    diagnostics_data: dict[str, Any] = {
        "config_entry": async_redact_data(config_entry.as_dict(), TO_REDACT)
    }

    if config_entry.data[CONF_FLOW_TYPE] == CONF_DEVICE:
        coordinator = config_entry.runtime_data.device_coordinator
        if isinstance(coordinator.data, dict):
            diagnostics_data["coordinator_data"] = coordinator.data
        else:
            diagnostics_data["coordinator_data"] = repr(coordinator.data)
    return diagnostics_data
