"""The Hong Kong Observatory integration."""

from __future__ import annotations

from hko import LOCATIONS

from menuai.const import CONF_LOCATION, Platform
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession

from .const import DEFAULT_DISTRICT, KEY_DISTRICT, KEY_LOCATION
from .coordinator import HKOConfigEntry, HKOUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.WEATHER]


async def async_setup_entry(menuai: menuai, entry: HKOConfigEntry) -> bool:
    """Set up Hong Kong Observatory from a config entry."""

    location = entry.data[CONF_LOCATION]
    district = next(
        (item for item in LOCATIONS if item[KEY_LOCATION] == location),
        {KEY_DISTRICT: DEFAULT_DISTRICT},
    )[KEY_DISTRICT]
    websession = async_get_clientsession(menuai)

    coordinator = HKOUpdateCoordinator(menuai, entry, websession, district, location)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: HKOConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
