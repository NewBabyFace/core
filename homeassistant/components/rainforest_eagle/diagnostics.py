"""Diagnostics support for Eagle."""

from __future__ import annotations

from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.config_entries import ConfigEntry
from menuai.core import menuai

from .const import CONF_CLOUD_ID, CONF_INSTALL_CODE, DOMAIN
from .coordinator import EagleDataCoordinator

TO_REDACT = {CONF_CLOUD_ID, CONF_INSTALL_CODE}


async def async_get_config_entry_diagnostics(
    menuai: menuai, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: EagleDataCoordinator = menuai.data[DOMAIN][config_entry.entry_id]

    return {
        "config_entry": async_redact_data(config_entry.as_dict(), TO_REDACT),
        "data": coordinator.data,
    }
