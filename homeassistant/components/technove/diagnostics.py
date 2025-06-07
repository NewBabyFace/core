"""Diagnostics support for TechnoVE."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.core import menuai

from .coordinator import TechnoVEConfigEntry

TO_REDACT = {"unique_id", "mac_address"}


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: TechnoVEConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    return async_redact_data(asdict(entry.runtime_data.data.info), TO_REDACT)
