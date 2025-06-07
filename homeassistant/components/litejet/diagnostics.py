"""Support for LiteJet diagnostics."""

from typing import Any

from pylitejet import LiteJet

from menuai.config_entries import ConfigEntry
from menuai.core import menuai

from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for LiteJet config entry."""
    system: LiteJet = menuai.data[DOMAIN]
    return {
        "model": system.model_name,
        "loads": list(system.loads()),
        "button_switches": list(system.button_switches()),
        "scenes": list(system.scenes()),
        "connected": system.connected,
    }
