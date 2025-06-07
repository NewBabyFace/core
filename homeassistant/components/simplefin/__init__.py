"""The SimpleFIN integration."""

from __future__ import annotations

from simplefin4py import SimpleFin

from menuai.const import Platform
from menuai.core import menuai

from .const import CONF_ACCESS_URL
from .coordinator import SimpleFinConfigEntry, SimpleFinDataUpdateCoordinator

PLATFORMS: list[str] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
]


async def async_setup_entry(menuai: menuai, entry: SimpleFinConfigEntry) -> bool:
    """Set up from a config entry."""
    access_url = entry.data[CONF_ACCESS_URL]
    sf_client = SimpleFin(access_url)
    sf_coordinator = SimpleFinDataUpdateCoordinator(menuai, entry, sf_client)
    await sf_coordinator.async_config_entry_first_refresh()
    entry.runtime_data = sf_coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: SimpleFinConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
