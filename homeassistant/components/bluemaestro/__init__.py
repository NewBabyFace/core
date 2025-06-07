"""The BlueMaestro integration."""

from __future__ import annotations

import logging

from bluemaestro_ble import BlueMaestroBluetoothDeviceData

from menuai.components.bluetooth import BluetoothScanningMode
from menuai.components.bluetooth.passive_update_processor import (
    PassiveBluetoothProcessorCoordinator,
)
from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai

PLATFORMS: list[Platform] = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)

type BlueMaestroConfigEntry = ConfigEntry[PassiveBluetoothProcessorCoordinator]


async def async_setup_entry(menuai: menuai, entry: BlueMaestroConfigEntry) -> bool:
    """Set up BlueMaestro BLE device from a config entry."""
    address = entry.unique_id
    assert address is not None
    data = BlueMaestroBluetoothDeviceData()
    coordinator = PassiveBluetoothProcessorCoordinator(
        menuai,
        _LOGGER,
        address=address,
        mode=BluetoothScanningMode.PASSIVE,
        update_method=data.update,
    )
    entry.runtime_data = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(
        coordinator.async_start()
    )  # only start after all platforms have had a chance to subscribe
    return True


async def async_unload_entry(
    menuai: menuai, entry: BlueMaestroConfigEntry
) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
