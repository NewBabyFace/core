"""SmartTub integration."""

from menuai.const import Platform
from menuai.core import menuai

from .controller import SmartTubConfigEntry, SmartTubController

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.LIGHT,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(menuai: menuai, entry: SmartTubConfigEntry) -> bool:
    """Set up a smarttub config entry."""

    controller = SmartTubController(menuai)

    if not await controller.async_setup_entry(entry):
        return False

    entry.runtime_data = controller

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: SmartTubConfigEntry) -> bool:
    """Remove a smarttub config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
