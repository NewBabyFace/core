"""Platform for the Escea fireplace."""

from menuai.components.climate import DOMAIN as CLIMATE_DOMAIN
from menuai.config_entries import ConfigEntry
from menuai.core import menuai

from .discovery import async_start_discovery_service, async_stop_discovery_service

PLATFORMS = [CLIMATE_DOMAIN]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    await async_start_discovery_service(menuai)
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload the config entry and stop discovery process."""
    await async_stop_discovery_service(menuai)
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
