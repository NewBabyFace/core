"""Diagnostics support for ViCare."""

from __future__ import annotations

import json
from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.const import CONF_CLIENT_ID, CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai

from .types import ViCareConfigEntry

TO_REDACT = {CONF_CLIENT_ID, CONF_PASSWORD, CONF_USERNAME}


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: ViCareConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    def dump_devices() -> list[dict[str, Any]]:
        """Dump devices."""
        return [
            json.loads(device.dump_secure())
            for device in entry.runtime_data.client.devices
        ]

    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "data": await menuai.async_add_executor_job(dump_devices),
    }
