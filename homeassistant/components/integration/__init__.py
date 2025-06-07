"""The Integration integration."""

from __future__ import annotations

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers.device import (
    async_remove_stale_devices_links_keep_entity_device,
)

from .const import CONF_SOURCE_SENSOR


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Integration from a config entry."""

    async_remove_stale_devices_links_keep_entity_device(
        menuai,
        entry.entry_id,
        entry.options[CONF_SOURCE_SENSOR],
    )

    await menuai.config_entries.async_forward_entry_setups(entry, (Platform.SENSOR,))
    entry.async_on_unload(entry.add_update_listener(config_entry_update_listener))
    return True


async def config_entry_update_listener(menuai: menuai, entry: ConfigEntry) -> None:
    """Update listener, called when the config entry options are changed."""
    # Remove device link for entry, the source device may have changed.
    # The link will be recreated after load.
    await menuai.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, (Platform.SENSOR,))
