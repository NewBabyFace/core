"""The FAA Delays integration."""

from menuai.const import CONF_ID, Platform
from menuai.core import menuai

from .coordinator import FAAConfigEntry, FAADataUpdateCoordinator

PLATFORMS = [Platform.BINARY_SENSOR]


async def async_setup_entry(menuai: menuai, entry: FAAConfigEntry) -> bool:
    """Set up FAA Delays from a config entry."""
    code = entry.data[CONF_ID]

    coordinator = FAADataUpdateCoordinator(menuai, entry, code)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: FAAConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
