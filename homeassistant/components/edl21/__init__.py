"""The edl21 component."""

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(menuai: menuai, config_entry: ConfigEntry) -> bool:
    """Set up EDL21 integration from a config entry."""
    await menuai.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(config_entry, PLATFORMS)
