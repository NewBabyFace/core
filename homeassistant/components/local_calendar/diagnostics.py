"""Provides diagnostics for local calendar."""

import datetime
from typing import Any

from ical.diagnostics import redact_ics

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.util import dt as dt_util

from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    menuai: menuai, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    payload: dict[str, Any] = {
        "now": dt_util.now().isoformat(),
        "timezone": str(dt_util.get_default_time_zone()),
        "system_timezone": str(datetime.datetime.now().astimezone().tzinfo),
    }
    store = menuai.data[DOMAIN][config_entry.entry_id]
    ics = await store.async_load()
    payload["ics"] = "\n".join(redact_ics(ics))
    return payload
