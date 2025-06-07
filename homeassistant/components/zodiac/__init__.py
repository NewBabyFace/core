"""The zodiac component."""

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Load a config entry."""
    await menuai.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, [Platform.SENSOR])
