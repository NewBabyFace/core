"""Support for the OSO Energy devices and services."""

from typing import Any

from aiohttp.web_exceptions import HTTPException
from apyosoenergyapi import OSOEnergy
from apyosoenergyapi.helper.osoenergy_exceptions import OSOEnergyReauthRequired

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_API_KEY, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from menuai.helpers import aiohttp_client

from .const import DOMAIN

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.WATER_HEATER,
]
PLATFORM_LOOKUP = {
    Platform.BINARY_SENSOR: "binary_sensor",
    Platform.SENSOR: "sensor",
    Platform.WATER_HEATER: "water_heater",
}


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up OSO Energy from a config entry."""
    subscription_key = entry.data[CONF_API_KEY]
    websession = aiohttp_client.async_get_clientsession(menuai)
    osoenergy = OSOEnergy(subscription_key, websession)

    osoenergy_config = dict(entry.data)

    menuai.data.setdefault(DOMAIN, {})

    try:
        devices: Any = await osoenergy.session.start_session(osoenergy_config)
    except HTTPException as error:
        raise ConfigEntryNotReady from error
    except OSOEnergyReauthRequired as err:
        raise ConfigEntryAuthFailed from err

    menuai.data[DOMAIN][entry.entry_id] = osoenergy

    platforms = set()
    for ha_type, oso_type in PLATFORM_LOOKUP.items():
        device_list = devices.get(oso_type, [])
        if device_list:
            platforms.add(ha_type)
    if platforms:
        await menuai.config_entries.async_forward_entry_setups(entry, platforms)
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
