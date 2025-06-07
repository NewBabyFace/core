"""Diagnostics support for CPU Speed."""

from __future__ import annotations

from typing import Any

from cpuinfo import cpuinfo

from menuai.config_entries import ConfigEntry
from menuai.core import menuai


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    info: dict[str, Any] = cpuinfo.get_cpu_info()
    return info
