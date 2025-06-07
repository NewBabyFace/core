"""The ThermoPro Bluetooth integration."""

from __future__ import annotations

from functools import partial
import logging

from thermopro_ble import SensorUpdate, ThermoProBluetoothDeviceData

from menuai.components.bluetooth import (
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
)
from menuai.components.bluetooth.passive_update_processor import (
    PassiveBluetoothProcessorCoordinator,
)
from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, SIGNAL_DATA_UPDATED

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS: list[Platform] = [Platform.BUTTON, Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


def process_service_info(
    menuai: menuai,
    entry: ConfigEntry,
    data: ThermoProBluetoothDeviceData,
    service_info: BluetoothServiceInfoBleak,
) -> SensorUpdate:
    """Process a BluetoothServiceInfoBleak, running side effects and returning sensor data."""
    update = data.update(service_info)
    async_dispatcher_send(
        menuai, f"{SIGNAL_DATA_UPDATED}_{entry.entry_id}", data, service_info, update
    )
    return update


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up ThermoPro BLE device from a config entry."""
    address = entry.unique_id
    assert address is not None
    data = ThermoProBluetoothDeviceData()
    coordinator = menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = (
        PassiveBluetoothProcessorCoordinator(
            menuai,
            _LOGGER,
            address=address,
            mode=BluetoothScanningMode.ACTIVE,
            update_method=partial(process_service_info, menuai, entry, data),
        )
    )
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # only start after all platforms have had a chance to subscribe
    entry.async_on_unload(coordinator.async_start())
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
