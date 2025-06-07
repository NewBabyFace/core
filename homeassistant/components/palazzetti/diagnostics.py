"""Provides diagnostics for Palazzetti."""

from __future__ import annotations

from typing import Any

from menuai.core import menuai

from .coordinator import PalazzettiConfigEntry


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: PalazzettiConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    client = entry.runtime_data.client

    return {
        "api_data": client.to_dict(redact=True),
    }
