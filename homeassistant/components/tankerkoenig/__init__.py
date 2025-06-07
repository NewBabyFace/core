"""Ask tankerkoenig.de for petrol price information."""

from __future__ import annotations

from menuai.const import Platform
from menuai.core import menuai

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import TankerkoenigConfigEntry, TankerkoenigDataUpdateCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(
    menuai: menuai, entry: TankerkoenigConfigEntry
) -> bool:
    """Set a tankerkoenig configuration entry up."""
    menuai.data.setdefault(DOMAIN, {})

    coordinator = TankerkoenigDataUpdateCoordinator(menuai, entry, DEFAULT_SCAN_INTERVAL)
    await coordinator.async_setup()
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    menuai: menuai, entry: TankerkoenigConfigEntry
) -> bool:
    """Unload Tankerkoenig config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(
    menuai: menuai, entry: TankerkoenigConfigEntry
) -> None:
    """Handle options update."""
    await menuai.config_entries.async_reload(entry.entry_id)
