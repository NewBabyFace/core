"""The Webmin integration."""

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai

from .coordinator import WebminUpdateCoordinator

PLATFORMS = [Platform.SENSOR]

type WebminConfigEntry = ConfigEntry[WebminUpdateCoordinator]


async def async_setup_entry(menuai: menuai, entry: WebminConfigEntry) -> bool:
    """Set up Webmin from a config entry."""

    coordinator = WebminUpdateCoordinator(menuai, entry)
    await coordinator.async_config_entry_first_refresh()
    await coordinator.async_setup()
    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: WebminConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
