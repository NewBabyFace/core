"""The Music Player Daemon integration."""

from __future__ import annotations

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai

PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Music Player Daemon from a config entry."""

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
