"""Diagnostics support for Fast.com."""

from __future__ import annotations

from typing import Any

from menuai.core import menuai

from .coordinator import FastdotcomConfigEntry


async def async_get_config_entry_diagnostics(
    menuai: menuai, config_entry: FastdotcomConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for the config entry."""
    return {"coordinator_data": config_entry.runtime_data.data}
