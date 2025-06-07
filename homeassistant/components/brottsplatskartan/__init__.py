"""The brottsplatskartan component."""

from __future__ import annotations

from menuai.config_entries import ConfigEntry
from menuai.core import menuai

from .const import PLATFORMS


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up brottsplatskartan from a config entry."""

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload brottsplatskartan config entry."""

    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
