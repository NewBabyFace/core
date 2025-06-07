"""Diagnostics support for WattTime."""

from __future__ import annotations

from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.config_entries import ConfigEntry
from menuai.const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_PASSWORD,
    CONF_UNIQUE_ID,
    CONF_USERNAME,
)
from menuai.core import menuai
from menuai.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_BALANCING_AUTHORITY, CONF_BALANCING_AUTHORITY_ABBREV, DOMAIN

CONF_TITLE = "title"

TO_REDACT = {
    CONF_BALANCING_AUTHORITY,
    CONF_BALANCING_AUTHORITY_ABBREV,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_PASSWORD,
    # Config entry title and unique ID may contain sensitive data:
    CONF_TITLE,
    CONF_UNIQUE_ID,
    CONF_USERNAME,
}


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: DataUpdateCoordinator = menuai.data[DOMAIN][entry.entry_id]

    return async_redact_data(
        {
            "entry": entry.as_dict(),
            "data": coordinator.data,
        },
        TO_REDACT,
    )
