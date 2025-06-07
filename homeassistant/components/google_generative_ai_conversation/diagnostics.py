"""Diagnostics support for Google Generative AI Conversation."""

from __future__ import annotations

from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_API_KEY
from menuai.core import menuai

TO_REDACT = {CONF_API_KEY}


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    return async_redact_data(
        {
            "title": entry.title,
            "data": entry.data,
            "options": entry.options,
        },
        TO_REDACT,
    )
