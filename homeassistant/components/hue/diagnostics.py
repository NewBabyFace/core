"""Diagnostics support for Hue."""

from __future__ import annotations

from typing import Any

from menuai.core import menuai

from .bridge import HueConfigEntry


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: HueConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    bridge = entry.runtime_data
    if bridge.api_version == 1:
        # diagnostics is only implemented for V2 bridges.
        return {}
    # Hue diagnostics are already redacted
    return await bridge.api.get_diagnostics()
