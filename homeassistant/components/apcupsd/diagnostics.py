"""Diagnostics support for APCUPSD."""

from __future__ import annotations

from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.core import menuai

from .coordinator import APCUPSdConfigEntry

TO_REDACT = {"SERIALNO", "HOSTNAME"}


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: APCUPSdConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    data = coordinator.data
    return async_redact_data(data, TO_REDACT)
