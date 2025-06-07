"""Diagnostics support for Rituals Perfume Genie."""

from __future__ import annotations

from typing import Any

from menuai.components.diagnostics import async_redact_data
from menuai.config_entries import ConfigEntry
from menuai.core import menuai

from .const import DOMAIN
from .coordinator import RitualsDataUpdateCoordinator

TO_REDACT = {
    "hublot",
    "hash",
}


async def async_get_config_entry_diagnostics(
    menuai: menuai, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinators: dict[str, RitualsDataUpdateCoordinator] = menuai.data[DOMAIN][
        entry.entry_id
    ]
    return {
        "diffusers": [
            async_redact_data(coordinator.diffuser.data, TO_REDACT)
            for coordinator in coordinators.values()
        ]
    }
