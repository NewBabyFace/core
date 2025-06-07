"""Diagnostics for the Cookidoo integration."""

from dataclasses import asdict
from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.const import CONF_PASSWORD
from menuai.core import menuai

from .coordinator import CookidooConfigEntry

TO_REDACT = [
    CONF_PASSWORD,
]


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: CookidooConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    return {
        "entry_data": async_redact_data(entry.data, TO_REDACT),
        "data": asdict(entry.runtime_data.data),
        "user": asdict(entry.runtime_data.user),
    }
