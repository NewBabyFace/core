"""Diagnostics support for Verisure."""

from __future__ import annotations

from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.config_entries import ConfigEntry
from menuai.core import menuai

from .const import DOMAIN
from .coordinator import VerisureDataUpdateCoordinator

TO_REDACT = {
    "date",
    "area",
    "deviceArea",
    "name",
    "time",
    "reportTime",
    "userString",
}


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: VerisureDataUpdateCoordinator = menuai.data[DOMAIN][entry.entry_id]
    return async_redact_data(coordinator.data, TO_REDACT)
