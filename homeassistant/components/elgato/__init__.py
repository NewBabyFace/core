"""Support for Elgato Lights."""

from menuai.const import Platform
from menuai.core import menuai

from .coordinator import ElgatoConfigEntry, ElgatoDataUpdateCoordinator

PLATFORMS = [Platform.BUTTON, Platform.LIGHT, Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(menuai: menuai, entry: ElgatoConfigEntry) -> bool:
    """Set up Elgato Light from a config entry."""
    coordinator = ElgatoDataUpdateCoordinator(menuai, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ElgatoConfigEntry) -> bool:
    """Unload Elgato Light config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
