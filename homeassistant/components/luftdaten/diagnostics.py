"""Diagnostics support for Sensor.Community."""

from __future__ import annotations

from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_LATITUDE, CONF_LONGITUDE
from menuai.core import menuai
from menuai.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_SENSOR_ID, DOMAIN

TO_REDACT = {
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_SENSOR_ID,
}


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: DataUpdateCoordinator[dict[str, Any]] = menuai.data[DOMAIN][
        entry.entry_id
    ]
    return async_redact_data(coordinator.data, TO_REDACT)
