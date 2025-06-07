"""The Rmenuaipy integration."""

from __future__ import annotations

from menuai.config_entries import ConfigEntry
from menuai.core import menuai


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Rmenuaipy from a config entry."""
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return True
