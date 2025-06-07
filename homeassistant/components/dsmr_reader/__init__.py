"""The DSMR Reader component."""

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up the DSMR Reader integration."""
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload the DSMR Reader integration."""
    # no data stored in menuai.data
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
