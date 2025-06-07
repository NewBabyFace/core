"""The Improv BLE integration."""

from __future__ import annotations

from menuai.config_entries import ConfigEntry
from menuai.core import menuai


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up improv_ble from a config entry."""
    raise NotImplementedError
