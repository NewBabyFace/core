"""Support for the QNAP QSW diagnostics."""

from __future__ import annotations

from typing import Any

from aioqsw.const import QSD_MAC, QSD_SERIAL

from menuai.components.diagnostics import async_redact_data
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_PASSWORD, CONF_UNIQUE_ID, CONF_USERNAME
from menuai.core import menuai

from .const import DOMAIN, QSW_COORD_DATA, QSW_COORD_FW
from .coordinator import QswDataCoordinator, QswFirmwareCoordinator

TO_REDACT_CONFIG = [
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_UNIQUE_ID,
]

TO_REDACT_DATA = [
    QSD_MAC,
    QSD_SERIAL,
]


async def async_get_config_entry_diagnostics(
    menuai: menuai, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    entry_data = menuai.data[DOMAIN][config_entry.entry_id]
    coord_data: QswDataCoordinator = entry_data[QSW_COORD_DATA]
    coord_fw: QswFirmwareCoordinator = entry_data[QSW_COORD_FW]

    return {
        "config_entry": async_redact_data(config_entry.as_dict(), TO_REDACT_CONFIG),
        "coord_data": async_redact_data(coord_data.data, TO_REDACT_DATA),
        "coord_fw": async_redact_data(coord_fw.data, TO_REDACT_DATA),
    }
