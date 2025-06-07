"""Diagnostics support for Nord Pool."""

from __future__ import annotations

from typing import Any

from menuai.core import menuai

from . import NordPoolConfigEntry


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: NordPoolConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for Nord Pool config entry."""
    return {"raw": entry.runtime_data.data.raw}
