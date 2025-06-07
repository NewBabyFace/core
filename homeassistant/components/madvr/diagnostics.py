"""Provides diagnostics for madVR."""

from __future__ import annotations

from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.const import CONF_HOST
from menuai.core import menuai

from .coordinator import MadVRConfigEntry

TO_REDACT = [CONF_HOST]


async def async_get_config_entry_diagnostics(
    menuai: menuai, config_entry: MadVRConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = config_entry.runtime_data.data

    return {
        "config_entry": async_redact_data(config_entry.as_dict(), TO_REDACT),
        "madvr_data": data,
    }
