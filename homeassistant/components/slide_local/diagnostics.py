"""Provides diagnostics for slide_local."""

from __future__ import annotations

from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.const import CONF_PASSWORD
from menuai.core import menuai

from .coordinator import SlideConfigEntry

TO_REDACT = [
    CONF_PASSWORD,
]


async def async_get_config_entry_diagnostics(
    menuai: menuai, config_entry: SlideConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = config_entry.runtime_data.data

    return {
        "config_entry": async_redact_data(config_entry.as_dict(), TO_REDACT),
        "slide_data": data,
    }
