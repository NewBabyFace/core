"""The dwd_weather_warnings component."""

from __future__ import annotations

from menuai.core import menuai
from menuai.helpers import device_registry as dr

from .const import DOMAIN, PLATFORMS
from .coordinator import DwdWeatherWarningsConfigEntry, DwdWeatherWarningsCoordinator


async def async_setup_entry(
    menuai: menuai, entry: DwdWeatherWarningsConfigEntry
) -> bool:
    """Set up a config entry."""
    device_registry = dr.async_get(menuai)
    if device_registry.async_get_device(identifiers={(DOMAIN, entry.entry_id)}):
        device_registry.async_clear_config_entry(entry.entry_id)
    coordinator = DwdWeatherWarningsCoordinator(menuai, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    menuai: menuai, entry: DwdWeatherWarningsConfigEntry
) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
