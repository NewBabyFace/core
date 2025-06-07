"""Diagnostics support for Yale Smart Alarm."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.core import menuai

from . import YaleConfigEntry

TO_REDACT = {
    "address",
    "name",
    "mac",
    "device_id",
    "user_id",
    "id",
    "mail_address",
    "report_account",
}


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: YaleConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data

    assert coordinator.yale
    get_all_data = await menuai.async_add_executor_job(coordinator.yale.get_all)
    return async_redact_data(asdict(get_all_data), TO_REDACT)
