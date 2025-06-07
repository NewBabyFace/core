"""Diagnostics support for OpenUV."""

from __future__ import annotations

from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.config_entries import ConfigEntry
from menuai.const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_UNIQUE_ID,
)
from menuai.core import menuai

from .const import DOMAIN
from .coordinator import OpenUvCoordinator

CONF_COORDINATES = "coordinates"
CONF_TITLE = "title"

TO_REDACT = {
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    # Config entry title and unique ID may contain sensitive data:
    CONF_TITLE,
    CONF_UNIQUE_ID,
}


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinators: dict[str, OpenUvCoordinator] = menuai.data[DOMAIN][entry.entry_id]

    return async_redact_data(
        {
            "entry": entry.as_dict(),
            "data": {
                coordinator_name: coordinator.data
                for coordinator_name, coordinator in coordinators.items()
            },
        },
        TO_REDACT,
    )
