"""Diagnostics support for IMAP."""

from __future__ import annotations

from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai, callback

from . import ImapConfigEntry

REDACT_CONFIG = {CONF_PASSWORD, CONF_USERNAME}


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: ImapConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    return _async_get_diagnostics(menuai, entry)


@callback
def _async_get_diagnostics(
    menuai: menuai,
    entry: ImapConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    redacted_config = async_redact_data(entry.data, REDACT_CONFIG)
    coordinator = entry.runtime_data

    return {
        "config": redacted_config,
        "event": coordinator.diagnostics_data,
    }
