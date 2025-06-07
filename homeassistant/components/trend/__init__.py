"""A sensor that monitors trends in other components."""

from __future__ import annotations

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.helpers.device import (
    async_remove_stale_devices_links_keep_entity_device,
)

PLATFORMS = [Platform.BINARY_SENSOR]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Trend from a config entry."""

    async_remove_stale_devices_links_keep_entity_device(
        menuai,
        entry.entry_id,
        entry.options[CONF_ENTITY_ID],
    )

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(config_entry_update_listener))

    return True


async def config_entry_update_listener(menuai: menuai, entry: ConfigEntry) -> None:
    """Handle an Trend options update."""
    await menuai.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
