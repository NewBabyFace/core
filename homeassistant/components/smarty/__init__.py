"""Support to control a Salda Smarty XP/XV ventilation unit."""

from menuai.const import Platform
from menuai.core import menuai

from .coordinator import SmartyConfigEntry, SmartyCoordinator

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.FAN,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(menuai: menuai, entry: SmartyConfigEntry) -> bool:
    """Set up the Smarty environment from a config entry."""

    coordinator = SmartyCoordinator(menuai, entry)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: SmartyConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
