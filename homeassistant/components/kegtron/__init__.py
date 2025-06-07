"""The Kegtron integration."""

from __future__ import annotations

import logging

from kegtron_ble import KegtronBluetoothDeviceData

from menuai.components.bluetooth import BluetoothScanningMode
from menuai.components.bluetooth.passive_update_processor import (
    PassiveBluetoothProcessorCoordinator,
)
from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai

from .const import DOMAIN

PLATFORMS: list[Platform] = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Kegtron BLE device from a config entry."""
    address = entry.unique_id
    assert address is not None
    data = KegtronBluetoothDeviceData()
    coordinator = menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = (
        PassiveBluetoothProcessorCoordinator(
            menuai,
            _LOGGER,
            address=address,
            mode=BluetoothScanningMode.PASSIVE,
            update_method=data.update,
        )
    )
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(
        coordinator.async_start()
    )  # only start after all platforms have had a chance to subscribe
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
