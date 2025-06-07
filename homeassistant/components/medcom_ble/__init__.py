"""The Medcom BLE integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from bleak import BleakError
from medcom_ble import MedcomBleDeviceData

from menuai.components import bluetooth
from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from menuai.util.unit_system import METRIC_SYSTEM

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

# Supported platforms
PLATFORMS: list[Platform] = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Medcom BLE radiation monitor from a config entry."""

    address = entry.unique_id
    elevation = menuai.config.elevation
    is_metric = menuai.config.units is METRIC_SYSTEM
    assert address is not None

    ble_device = bluetooth.async_ble_device_from_address(menuai, address)
    if not ble_device:
        raise ConfigEntryNotReady(
            f"Could not find Medcom BLE device with address {address}"
        )

    async def _async_update_method():
        """Get data from Medcom BLE radiation monitor."""
        ble_device = bluetooth.async_ble_device_from_address(menuai, address)
        inspector = MedcomBleDeviceData(_LOGGER, elevation, is_metric)

        try:
            data = await inspector.update_device(ble_device)
        except BleakError as err:
            raise UpdateFailed(f"Unable to fetch data: {err}") from err

        return data

    coordinator = DataUpdateCoordinator(
        menuai,
        _LOGGER,
        config_entry=entry,
        name=DOMAIN,
        update_method=_async_update_method,
        update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
    )

    await coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
