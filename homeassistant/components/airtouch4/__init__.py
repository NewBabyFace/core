"""The AirTouch4 integration."""

from airtouch4pyapi import AirTouch

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady

from .coordinator import AirtouchDataUpdateCoordinator

PLATFORMS = [Platform.CLIMATE]

type AirTouch4ConfigEntry = ConfigEntry[AirtouchDataUpdateCoordinator]


async def async_setup_entry(menuai: menuai, entry: AirTouch4ConfigEntry) -> bool:
    """Set up AirTouch4 from a config entry."""
    host = entry.data[CONF_HOST]
    airtouch = AirTouch(host)
    await airtouch.UpdateInfo()
    info = airtouch.GetAcs()
    if not info:
        raise ConfigEntryNotReady
    coordinator = AirtouchDataUpdateCoordinator(menuai, airtouch)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: AirTouch4ConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
