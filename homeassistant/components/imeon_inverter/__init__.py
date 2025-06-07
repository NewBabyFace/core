"""Initialize the Imeon component."""

from __future__ import annotations

import logging

from menuai.core import menuai

from .const import PLATFORMS
from .coordinator import InverterConfigEntry, InverterCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: InverterConfigEntry) -> bool:
    """Handle the creation of a new config entry for the integration (asynchronous)."""

    # Create the corresponding HUB
    coordinator = InverterCoordinator(menuai, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    # Call for HUB creation then each entity as a List
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: InverterConfigEntry) -> bool:
    """Handle entry unloading."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
