"""Diagnostics support for bluetooth."""

from __future__ import annotations

import platform
from typing import Any

from bluetooth_adapters import get_dbus_managed_objects

from menuai.config_entries import ConfigEntry
from menuai.core import menuai

from .api import _get_manager


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    manager = _get_manager(menuai)
    manager_diagnostics = await manager.async_diagnostics()
    adapters = await manager.async_get_bluetooth_adapters()
    diagnostics = {
        "manager": manager_diagnostics,
        "adapters": adapters,
    }
    if platform.system() == "Linux":
        diagnostics["dbus"] = await get_dbus_managed_objects()
    return diagnostics
