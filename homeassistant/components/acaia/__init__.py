"""Initialize the Acaia component."""

from menuai.const import Platform
from menuai.core import menuai

from .coordinator import AcaiaConfigEntry, AcaiaCoordinator

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SENSOR,
]


async def async_setup_entry(menuai: menuai, entry: AcaiaConfigEntry) -> bool:
    """Set up acaia as config entry."""

    coordinator = AcaiaCoordinator(menuai, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: AcaiaConfigEntry) -> bool:
    """Unload a config entry."""

    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
