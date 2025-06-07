"""The PurpleAir integration."""

from __future__ import annotations

from menuai.core import menuai

from .const import PLATFORMS
from .coordinator import PurpleAirConfigEntry, PurpleAirDataUpdateCoordinator


async def async_setup_entry(menuai: menuai, entry: PurpleAirConfigEntry) -> bool:
    """Set up PurpleAir config entry."""
    coordinator = PurpleAirDataUpdateCoordinator(
        menuai,
        entry,
    )
    entry.runtime_data = coordinator

    await coordinator.async_config_entry_first_refresh()

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_reload_entry(menuai: menuai, entry: PurpleAirConfigEntry) -> None:
    """Reload config entry."""
    await menuai.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(menuai: menuai, entry: PurpleAirConfigEntry) -> bool:
    """Unload config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
