"""The Evil Genius Labs integration."""

from __future__ import annotations

import pyevilgenius

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import aiohttp_client

from .coordinator import EvilGeniusConfigEntry, EvilGeniusUpdateCoordinator

PLATFORMS = [Platform.LIGHT]

UPDATE_INTERVAL = 10


async def async_setup_entry(menuai: menuai, entry: EvilGeniusConfigEntry) -> bool:
    """Set up Evil Genius Labs from a config entry."""
    coordinator = EvilGeniusUpdateCoordinator(
        menuai,
        entry,
        pyevilgenius.EvilGeniusDevice(
            entry.data["host"], aiohttp_client.async_get_clientsession(menuai)
        ),
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: EvilGeniusConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
