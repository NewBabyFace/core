"""The Govee Bluetooth BLE integration."""

from __future__ import annotations

from functools import partial
import logging

from govee_ble import GoveeBluetoothDeviceData

from menuai.components.bluetooth import BluetoothScanningMode
from menuai.const import Platform
from menuai.core import menuai

from .coordinator import (
    GoveeBLEBluetoothProcessorCoordinator,
    GoveeBLEConfigEntry,
    process_service_info,
)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.EVENT, Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: GoveeBLEConfigEntry) -> bool:
    """Set up Govee BLE device from a config entry."""
    address = entry.unique_id
    assert address is not None
    data = GoveeBluetoothDeviceData()
    entry.runtime_data = coordinator = GoveeBLEBluetoothProcessorCoordinator(
        menuai,
        _LOGGER,
        address=address,
        mode=BluetoothScanningMode.ACTIVE,
        update_method=partial(process_service_info, menuai, entry),
        device_data=data,
        entry=entry,
    )
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # only start after all platforms have had a chance to subscribe
    entry.async_on_unload(coordinator.async_start())
    return True


async def async_unload_entry(menuai: menuai, entry: GoveeBLEConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
