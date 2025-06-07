"""Fetches diagnostic data for Starlink systems."""

from dataclasses import asdict
from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.core import menuai

from .coordinator import StarlinkConfigEntry

TO_REDACT = {"id", "latitude", "longitude", "altitude"}


async def async_get_config_entry_diagnostics(
    menuai: menuai, config_entry: StarlinkConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for Starlink config entries."""
    return async_redact_data(asdict(config_entry.runtime_data.data), TO_REDACT)
