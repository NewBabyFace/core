"""Amazon Devices integration."""

from menuai.const import Platform
from menuai.core import menuai

from .coordinator import AmazonConfigEntry, AmazonDevicesCoordinator

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.NOTIFY,
    Platform.SWITCH,
]


async def async_setup_entry(menuai: menuai, entry: AmazonConfigEntry) -> bool:
    """Set up Amazon Devices platform."""

    coordinator = AmazonDevicesCoordinator(menuai, entry)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: AmazonConfigEntry) -> bool:
    """Unload a config entry."""
    await entry.runtime_data.api.close()
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
