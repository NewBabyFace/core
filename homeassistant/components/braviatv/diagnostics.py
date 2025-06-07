"""Diagnostics support for BraviaTV."""

from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.const import CONF_MAC, CONF_PIN
from menuai.core import menuai

from .coordinator import BraviaTVConfigEntry

TO_REDACT = {CONF_MAC, CONF_PIN, "macAddr"}


async def async_get_config_entry_diagnostics(
    menuai: menuai, config_entry: BraviaTVConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = config_entry.runtime_data

    device_info = await coordinator.client.get_system_info()

    return {
        "config_entry": async_redact_data(config_entry.as_dict(), TO_REDACT),
        "device_info": async_redact_data(device_info, TO_REDACT),
    }
