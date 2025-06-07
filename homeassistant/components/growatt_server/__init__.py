"""The Growatt server PV inverter sensor integration."""

from menuai import config_entries
from menuai.config_entries import ConfigEntry
from menuai.core import menuai

from .const import PLATFORMS


async def async_setup_entry(
    menuai: menuai, entry: config_entries.ConfigEntry
) -> bool:
    """Load the saved entities."""

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
