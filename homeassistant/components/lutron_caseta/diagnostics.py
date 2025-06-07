"""Diagnostics support for lutron_caseta."""

from __future__ import annotations

from typing import Any

from menuai.config_entries import ConfigEntry
from menuai.core import menuai


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = entry.runtime_data
    bridge = data.bridge
    return {
        "entry": {
            "title": entry.title,
            "data": dict(entry.data),
        },
        "bridge_data": {
            "devices": bridge.devices,
            "buttons": bridge.buttons,
            "scenes": bridge.scenes,
            "occupancy_groups": bridge.occupancy_groups,
            "areas": bridge.areas,
        },
        "integration_data": {
            "keypad_button_names_to_leap": data.keypad_data.button_names_to_leap,
            "keypad_buttons": data.keypad_data.buttons,
            "keypads": data.keypad_data.keypads,
        },
    }
