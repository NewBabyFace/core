"""The iBeacon tracker integration."""

from __future__ import annotations

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers import device_registry as dr
from menuai.helpers.device_registry import DeviceEntry

from .const import DOMAIN, PLATFORMS
from .coordinator import IBeaconCoordinator

type IBeaconConfigEntry = ConfigEntry[IBeaconCoordinator]


async def async_setup_entry(menuai: menuai, entry: IBeaconConfigEntry) -> bool:
    """Set up Bluetooth LE Tracker from a config entry."""
    entry.runtime_data = coordinator = IBeaconCoordinator(
        menuai, entry, dr.async_get(menuai)
    )
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await coordinator.async_start()
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_config_entry_device(
    menuai: menuai, config_entry: IBeaconConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Remove iBeacon config entry from a device."""
    coordinator = config_entry.runtime_data
    return not any(
        identifier
        for identifier in device_entry.identifiers
        if identifier[0] == DOMAIN and coordinator.async_device_id_seen(identifier[1])
    )
