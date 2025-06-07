"""Integration for Crownstone."""

from __future__ import annotations

from menuai.const import EVENT_menuai_STOP
from menuai.core import menuai

from .const import PLATFORMS
from .entry_manager import CrownstoneConfigEntry, CrownstoneEntryManager


async def async_setup_entry(menuai: menuai, entry: CrownstoneConfigEntry) -> bool:
    """Initiate setup for a Crownstone config entry."""
    manager = CrownstoneEntryManager(menuai, entry)

    if not await manager.async_setup():
        return False

    entry.runtime_data = manager

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # HA specific listeners
    entry.async_on_unload(entry.add_update_listener(async_update_listener))
    entry.async_on_unload(
        menuai.bus.async_listen_once(EVENT_menuai_STOP, manager.on_shutdown)
    )

    return True


async def async_unload_entry(menuai: menuai, entry: CrownstoneConfigEntry) -> bool:
    """Unload a config entry."""
    entry.runtime_data.async_unload()

    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_update_listener(
    menuai: menuai, entry: CrownstoneConfigEntry
) -> None:
    """Handle options update."""
    await menuai.config_entries.async_reload(entry.entry_id)
