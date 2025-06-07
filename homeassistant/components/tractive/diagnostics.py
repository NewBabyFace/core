"""Diagnostics support for Tractive."""

from __future__ import annotations

from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.const import CONF_EMAIL, CONF_PASSWORD
from menuai.core import menuai

from . import TractiveConfigEntry

TO_REDACT = {CONF_PASSWORD, CONF_EMAIL, "title", "_id"}


async def async_get_config_entry_diagnostics(
    menuai: menuai, config_entry: TractiveConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    trackables = config_entry.runtime_data.trackables

    return async_redact_data(
        {
            "config_entry": config_entry.as_dict(),
            "trackables": [item.trackable for item in trackables],
        },
        TO_REDACT,
    )
