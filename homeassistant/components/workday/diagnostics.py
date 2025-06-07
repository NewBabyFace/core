"""Diagnostics support for Workday."""

from __future__ import annotations

from typing import Any

from menuai.config_entries import ConfigEntry
from menuai.core import menuai


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    return {
        "config_entry": entry,
    }
