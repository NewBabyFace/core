"""The Qingping integration."""

from __future__ import annotations

import logging

from qingping_ble import QingpingBluetoothDeviceData

from menuai.components.bluetooth import BluetoothScanningMode
from menuai.components.bluetooth.passive_update_processor import (
    PassiveBluetoothProcessorCoordinator,
)
from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)

type QingpingConfigEntry = ConfigEntry[PassiveBluetoothProcessorCoordinator]


async def async_setup_entry(menuai: menuai, entry: QingpingConfigEntry) -> bool:
    """Set up Qingping BLE device from a config entry."""
    address = entry.unique_id
    assert address is not None
    data = QingpingBluetoothDeviceData()
    coordinator = entry.runtime_data = PassiveBluetoothProcessorCoordinator(
        menuai,
        _LOGGER,
        address=address,
        mode=BluetoothScanningMode.PASSIVE,
        update_method=data.update,
    )
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # only start after all platforms have had a chance to subscribe
    entry.async_on_unload(coordinator.async_start())
    return True


async def async_unload_entry(menuai: menuai, entry: QingpingConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
