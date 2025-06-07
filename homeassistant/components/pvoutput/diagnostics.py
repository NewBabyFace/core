"""Diagnostics support for PVOutput."""

from __future__ import annotations

from typing import Any

from menuai.config_entries import ConfigEntry
from menuai.core import menuai

from .const import DOMAIN
from .coordinator import PVOutputDataUpdateCoordinator


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: PVOutputDataUpdateCoordinator = menuai.data[DOMAIN][entry.entry_id]
    return coordinator.data.to_dict()
