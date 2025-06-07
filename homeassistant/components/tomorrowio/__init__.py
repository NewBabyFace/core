"""The Tomorrow.io integration."""

from __future__ import annotations

from pytomorrowio import TomorrowioV4

from menuai.components.sensor import DOMAIN as SENSOR_DOMAIN
from menuai.components.weather import DOMAIN as WEATHER_DOMAIN
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_API_KEY
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .coordinator import TomorrowioDataUpdateCoordinator

PLATFORMS = [SENSOR_DOMAIN, WEATHER_DOMAIN]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Tomorrow.io API from a config entry."""
    menuai.data.setdefault(DOMAIN, {})

    api_key = entry.data[CONF_API_KEY]
    # If coordinator already exists for this API key, we'll use that, otherwise
    # we have to create a new one
    if not (coordinator := menuai.data[DOMAIN].get(api_key)):
        session = async_get_clientsession(menuai)
        # we will not use the class's lat and long so we can pass in garbage
        # lats and longs
        api = TomorrowioV4(api_key, 361.0, 361.0, unit_system="metric", session=session)
        coordinator = TomorrowioDataUpdateCoordinator(menuai, entry, api)
        menuai.data[DOMAIN][api_key] = coordinator

    await coordinator.async_setup_entry(entry)

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    api_key = config_entry.data[CONF_API_KEY]
    coordinator: TomorrowioDataUpdateCoordinator = menuai.data[DOMAIN][api_key]
    # If this is true, we can remove the coordinator
    if await coordinator.async_unload_entry(config_entry):
        menuai.data[DOMAIN].pop(api_key)
        if not menuai.data[DOMAIN]:
            menuai.data.pop(DOMAIN)

    return unload_ok
