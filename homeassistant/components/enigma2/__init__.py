"""Support for Enigma2 devices."""

from menuai.const import Platform
from menuai.core import menuai

from .coordinator import Enigma2ConfigEntry, Enigma2UpdateCoordinator

PLATFORMS = [Platform.MEDIA_PLAYER]


async def async_setup_entry(menuai: menuai, entry: Enigma2ConfigEntry) -> bool:
    """Set up Enigma2 from a config entry."""

    coordinator = Enigma2UpdateCoordinator(menuai, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: Enigma2ConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
