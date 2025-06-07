"""The iotawatt integration."""

from menuai.const import Platform
from menuai.core import menuai

from .coordinator import IotawattConfigEntry, IotawattUpdater

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: IotawattConfigEntry) -> bool:
    """Set up iotawatt from a config entry."""
    coordinator = IotawattUpdater(menuai, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: IotawattConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
