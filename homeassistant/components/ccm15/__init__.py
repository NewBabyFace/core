"""The Midea ccm15 AC Controller integration."""

from __future__ import annotations

from menuai.const import CONF_HOST, CONF_PORT, Platform
from menuai.core import menuai

from .coordinator import CCM15ConfigEntry, CCM15Coordinator

PLATFORMS: list[Platform] = [Platform.CLIMATE]


async def async_setup_entry(menuai: menuai, entry: CCM15ConfigEntry) -> bool:
    """Set up Midea ccm15 AC Controller from a config entry."""

    coordinator = CCM15Coordinator(
        menuai,
        entry,
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: CCM15ConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
