"""The buienradar integration."""

from __future__ import annotations

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai

from .util import BrData

PLATFORMS = [Platform.CAMERA, Platform.SENSOR, Platform.WEATHER]

type BuienRadarConfigEntry = ConfigEntry[dict[Platform, BrData]]


async def async_setup_entry(menuai: menuai, entry: BuienRadarConfigEntry) -> bool:
    """Set up buienradar from a config entry."""
    entry.runtime_data = {}
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_unload_entry(menuai: menuai, entry: BuienRadarConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        for platform in PLATFORMS:
            if (data := entry.runtime_data.get(platform)) and (
                unsub := data.unsub_schedule_update
            ):
                unsub()

    return unload_ok


async def async_update_options(
    menuai: menuai, config_entry: BuienRadarConfigEntry
) -> None:
    """Update options."""
    await menuai.config_entries.async_reload(config_entry.entry_id)
