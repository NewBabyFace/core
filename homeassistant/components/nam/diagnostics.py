"""Diagnostics support for NAM."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai

from .coordinator import NAMConfigEntry

TO_REDACT = {CONF_PASSWORD, CONF_USERNAME}


async def async_get_config_entry_diagnostics(
    menuai: menuai, config_entry: NAMConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = config_entry.runtime_data

    return {
        "info": async_redact_data(config_entry.data, TO_REDACT),
        "data": asdict(coordinator.data),
    }
