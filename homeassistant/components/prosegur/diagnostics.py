"""Diagnostics support for Prosegur."""

from __future__ import annotations

from typing import Any

from pyprosegur.installation import Installation

from menuai.components.diagnostics import async_redact_data
from menuai.config_entries import ConfigEntry
from menuai.core import menuai

from .const import CONF_CONTRACT, DOMAIN

TO_REDACT = {"description", "latitude", "longitude", "contractId", "address"}


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    installation = await Installation.retrieve(
        menuai.data[DOMAIN][entry.entry_id], entry.data[CONF_CONTRACT]
    )

    activity = await installation.activity(menuai.data[DOMAIN][entry.entry_id])

    return {
        "installation": async_redact_data(installation.data, TO_REDACT),
        "activity": activity,
    }
