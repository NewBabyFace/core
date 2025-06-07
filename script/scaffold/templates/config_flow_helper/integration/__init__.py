"""The NEW_NAME integration."""

from __future__ import annotations

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up NEW_NAME from a config entry."""
    # TODO Optionally store an object for your platforms to access
    # entry.runtime_data = ...

    # TODO Optionally validate config entry options before setting up platform

    await menuai.config_entries.async_forward_entry_setups(entry, (Platform.SENSOR,))

    # TODO Remove if the integration does not have an options flow
    entry.async_on_unload(entry.add_update_listener(config_entry_update_listener))

    return True


# TODO Remove if the integration does not have an options flow
async def config_entry_update_listener(menuai: menuai, entry: ConfigEntry) -> None:
    """Update listener, called when the config entry options are changed."""
    await menuai.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, (Platform.SENSOR,))
