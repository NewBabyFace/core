"""Diagnostics support for Launch Library."""

from __future__ import annotations

from typing import Any

from pylaunches.types import Event, Launch

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.update_coordinator import DataUpdateCoordinator

from . import LaunchLibraryData
from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    menuai: menuai,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    coordinator: DataUpdateCoordinator[LaunchLibraryData] = menuai.data[DOMAIN]
    if coordinator.data is None:
        return {}

    def _first_element(data: list[Launch | Event]) -> dict[str, Any] | None:
        if not data:
            return None
        return data[0]

    return {
        "next_launch": _first_element(coordinator.data["upcoming_launches"]),
        "starship_launch": _first_element(
            coordinator.data["starship_events"].upcoming.launches
        ),
        "starship_event": _first_element(
            coordinator.data["starship_events"].upcoming.events
        ),
    }
