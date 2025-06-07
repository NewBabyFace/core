"""Diagnostics platform for Russound RIO."""

from typing import Any

from menuai.core import menuai

from . import RussoundConfigEntry


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: RussoundConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for the provided config entry."""
    return entry.runtime_data.state
