"""Diagnostics for the EHEIM Digital integration."""

from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.core import menuai

from .coordinator import EheimDigitalConfigEntry

TO_REDACT = {"emailAddr", "usrName"}


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: EheimDigitalConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    return async_redact_data(
        {"entry": entry.as_dict(), "data": entry.runtime_data.data}, TO_REDACT
    )
