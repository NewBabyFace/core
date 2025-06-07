"""Diagnostics support for LIFX."""

from __future__ import annotations

from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, CONF_IP_ADDRESS, CONF_MAC
from menuai.core import menuai

from .const import CONF_LABEL, DOMAIN
from .coordinator import LIFXUpdateCoordinator

TO_REDACT = [CONF_LABEL, CONF_HOST, CONF_IP_ADDRESS, CONF_MAC]


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a LIFX config entry."""
    coordinator: LIFXUpdateCoordinator = menuai.data[DOMAIN][entry.entry_id]
    return {
        "entry": {
            "title": entry.title,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
        },
        "data": async_redact_data(await coordinator.diagnostics(), TO_REDACT),
    }
