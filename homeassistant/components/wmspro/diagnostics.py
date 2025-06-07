"""Diagnostics support for WMS WebControl pro API integration."""

from __future__ import annotations

from typing import Any

from menuai.core import menuai

from . import WebControlProConfigEntry


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: WebControlProConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    return entry.runtime_data.diag()
