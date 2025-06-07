"""The Times of the Day integration."""

from __future__ import annotations

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Times of the Day from a config entry."""
    await menuai.config_entries.async_forward_entry_setups(
        entry, (Platform.BINARY_SENSOR,)
    )

    entry.async_on_unload(entry.add_update_listener(config_entry_update_listener))

    return True


async def config_entry_update_listener(menuai: menuai, entry: ConfigEntry) -> None:
    """Update listener, called when the config entry options are changed."""
    await menuai.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(
        entry, (Platform.BINARY_SENSOR,)
    )
