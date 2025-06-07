"""Diagnostics support for Bring."""

from __future__ import annotations

from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.const import CONF_EMAIL, CONF_NAME
from menuai.core import menuai

from .coordinator import BringConfigEntry

TO_REDACT = {CONF_NAME, CONF_EMAIL}


async def async_get_config_entry_diagnostics(
    menuai: menuai, config_entry: BringConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    return {
        "data": {
            k: v.to_dict() for k, v in config_entry.runtime_data.data.data.items()
        },
        "activity": {
            k: async_redact_data(v.to_dict(), TO_REDACT)
            for k, v in config_entry.runtime_data.activity.data.items()
        },
        "lists": [lst.to_dict() for lst in config_entry.runtime_data.data.lists],
        "user_settings": config_entry.runtime_data.data.user_settings.to_dict(),
    }
