"""Diagnostics support for Whois."""

from __future__ import annotations

from typing import Any

from whois import Domain

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: DataUpdateCoordinator[Domain] = menuai.data[DOMAIN][entry.entry_id]
    return {
        "creation_date": coordinator.data.creation_date,
        "expiration_date": coordinator.data.expiration_date,
        "last_updated": coordinator.data.last_updated,
        "status": coordinator.data.status,
        "statuses": coordinator.data.statuses,
        "dnssec": coordinator.data.dnssec,
    }
