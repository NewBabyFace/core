"""The Ambient Weather Network integration."""

from __future__ import annotations

from aioambient.open_api import OpenAPI

from menuai.const import Platform
from menuai.core import menuai

from .coordinator import AmbientNetworkConfigEntry, AmbientNetworkDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(
    menuai: menuai, entry: AmbientNetworkConfigEntry
) -> bool:
    """Set up the Ambient Weather Network from a config entry."""

    api = OpenAPI()
    coordinator = AmbientNetworkDataUpdateCoordinator(menuai, entry, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    menuai: menuai, entry: AmbientNetworkConfigEntry
) -> bool:
    """Unload a config entry."""

    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
