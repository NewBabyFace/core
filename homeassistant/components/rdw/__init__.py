"""Support for RDW."""

from __future__ import annotations

from vehicle import RDW, Vehicle

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_LICENSE_PLATE, DOMAIN, LOGGER, SCAN_INTERVAL

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up RDW from a config entry."""
    session = async_get_clientsession(menuai)
    rdw = RDW(session=session, license_plate=entry.data[CONF_LICENSE_PLATE])

    coordinator: DataUpdateCoordinator[Vehicle] = DataUpdateCoordinator(
        menuai,
        LOGGER,
        config_entry=entry,
        name=f"{DOMAIN}_APK",
        update_interval=SCAN_INTERVAL,
        update_method=rdw.vehicle,
    )
    await coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload RDW config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        del menuai.data[DOMAIN][entry.entry_id]
    return unload_ok
