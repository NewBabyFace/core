"""The Airthings BLE integration."""

from __future__ import annotations

from menuai.const import Platform
from menuai.core import menuai

from .const import MAX_RETRIES_AFTER_STARTUP
from .coordinator import AirthingsBLEConfigEntry, AirthingsBLEDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(
    menuai: menuai, entry: AirthingsBLEConfigEntry
) -> bool:
    """Set up Airthings BLE device from a config entry."""
    coordinator = AirthingsBLEDataUpdateCoordinator(menuai, entry)
    await coordinator.async_config_entry_first_refresh()

    # Once its setup and we know we are not going to delay
    # the startup of MenuAI, we can set the max attempts
    # to a higher value. If the first connection attempt fails,
    # MenuAI's built-in retry logic will take over.
    coordinator.airthings.set_max_attempts(MAX_RETRIES_AFTER_STARTUP)

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    menuai: menuai, entry: AirthingsBLEConfigEntry
) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
