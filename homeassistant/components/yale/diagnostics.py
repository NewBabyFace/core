"""Diagnostics support for yale."""

from __future__ import annotations

from typing import Any

from yalexs.const import Brand

from menuai.components.diagnostics import async_redact_data
from menuai.core import menuai

from . import YaleConfigEntry

TO_REDACT = {
    "HouseID",
    "OfflineKeys",
    "installUserID",
    "invitations",
    "key",
    "pins",
    "pubsubChannel",
    "recentImage",
    "remoteOperateSecret",
    "users",
    "zWaveDSK",
    "contentToken",
}


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: YaleConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = entry.runtime_data

    return {
        "locks": {
            lock.device_id: async_redact_data(
                data.get_device_detail(lock.device_id).raw, TO_REDACT
            )
            for lock in data.locks
        },
        "doorbells": {
            doorbell.device_id: async_redact_data(
                data.get_device_detail(doorbell.device_id).raw, TO_REDACT
            )
            for doorbell in data.doorbells
        },
        "brand": Brand.YALE_GLOBAL.value,
    }
