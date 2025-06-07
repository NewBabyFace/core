"""Diagnostics support for Netatmo."""

from __future__ import annotations

from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.config_entries import ConfigEntry
from menuai.core import menuai

from .const import DATA_HANDLER, DOMAIN
from .data_handler import ACCOUNT, NetatmoDataHandler

TO_REDACT = {
    "access_token",
    "refresh_token",
    "restricted_access_token",
    "restricted_refresh_token",
    "webhook_id",
    "cloudhook_url",
    "lat_ne",
    "lat_sw",
    "lon_ne",
    "lon_sw",
    "coordinates",
    "name",
    "timetable",
    "zones",
    "pseudo",
    "url",
}


async def async_get_config_entry_diagnostics(
    menuai: menuai, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data_handler: NetatmoDataHandler = menuai.data[DOMAIN][config_entry.entry_id][
        DATA_HANDLER
    ]

    return {
        "info": async_redact_data(
            {
                **config_entry.as_dict(),
                "webhook_registered": data_handler.webhook,
            },
            TO_REDACT,
        ),
        "data": {
            ACCOUNT: async_redact_data(
                data_handler.account.raw_data,
                TO_REDACT,
            )
        },
    }
