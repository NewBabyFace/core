"""Diagnostics support for RDW."""

from __future__ import annotations

from typing import Any

from vehicle import Vehicle

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: DataUpdateCoordinator[Vehicle] = menuai.data[DOMAIN][entry.entry_id]
    data: dict[str, Any] = coordinator.data.to_dict()
    return data
