"""The CO2 Signal integration."""

from __future__ import annotations

from aioelectricitymaps import ElectricityMaps

from menuai.const import CONF_API_KEY, Platform
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession

from .coordinator import CO2SignalConfigEntry, CO2SignalCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: CO2SignalConfigEntry) -> bool:
    """Set up CO2 Signal from a config entry."""
    session = async_get_clientsession(menuai)
    coordinator = CO2SignalCoordinator(
        menuai, entry, ElectricityMaps(token=entry.data[CONF_API_KEY], session=session)
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: CO2SignalConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
