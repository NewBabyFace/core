"""The bluetooth integration apis.

These APIs are the only documented way to interact with the bluetooth integration.
"""

from __future__ import annotations

import asyncio
from asyncio import Future
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, cast

from habluetooth import (
    BaseHaScanner,
    BluetoothScannerDevice,
    BluetoothScanningMode,
    HaBleakScannerWrapper,
    get_manager,
)
from home_assistant_bluetooth import BluetoothServiceInfoBleak

from menuai.core import CALLBACK_TYPE, menuai, callback as menuai_callback
from menuai.helpers.singleton import singleton

from .const import DATA_MANAGER
from .manager import menuaiBluetoothManager
from .match import BluetoothCallbackMatcher
from .models import BluetoothCallback, BluetoothChange, ProcessAdvertisementCallback

if TYPE_CHECKING:
    from bleak.backends.device import BLEDevice


@singleton(DATA_MANAGER)
def _get_manager(menuai: menuai) -> menuaiBluetoothManager:
    """Get the bluetooth manager."""
    return cast(menuaiBluetoothManager, get_manager())


@menuai_callback
def async_get_scanner(menuai: menuai) -> HaBleakScannerWrapper:
    """Return a HaBleakScannerWrapper.

    This is a wrapper around our BleakScanner singleton that allows
    multiple integrations to share the same BleakScanner.
    """
    return HaBleakScannerWrapper()


@menuai_callback
def async_scanner_by_source(menuai: menuai, source: str) -> BaseHaScanner | None:
    """Return a scanner for a given source.

    This method is only intended to be used by integrations that implement
    a bluetooth client and need to interact with a scanner directly.

    It is not intended to be used by integrations that need to interact
    with a device.
    """
    return _get_manager(menuai).async_scanner_by_source(source)


@menuai_callback
def async_scanner_count(menuai: menuai, connectable: bool = True) -> int:
    """Return the number of scanners currently in use."""
    return _get_manager(menuai).async_scanner_count(connectable)


@menuai_callback
def async_discovered_service_info(
    menuai: menuai, connectable: bool = True
) -> Iterable[BluetoothServiceInfoBleak]:
    """Return the discovered devices list."""
    return _get_manager(menuai).async_discovered_service_info(connectable)


@menuai_callback
def async_last_service_info(
    menuai: menuai, address: str, connectable: bool = True
) -> BluetoothServiceInfoBleak | None:
    """Return the last service info for an address."""
    return _get_manager(menuai).async_last_service_info(address, connectable)


@menuai_callback
def async_ble_device_from_address(
    menuai: menuai, address: str, connectable: bool = True
) -> BLEDevice | None:
    """Return BLEDevice for an address if its present."""
    return _get_manager(menuai).async_ble_device_from_address(address, connectable)


@menuai_callback
def async_scanner_devices_by_address(
    menuai: menuai, address: str, connectable: bool = True
) -> list[BluetoothScannerDevice]:
    """Return all discovered BluetoothScannerDevice for an address."""
    return _get_manager(menuai).async_scanner_devices_by_address(address, connectable)


@menuai_callback
def async_address_present(
    menuai: menuai, address: str, connectable: bool = True
) -> bool:
    """Check if an address is present in the bluetooth device list."""
    return _get_manager(menuai).async_address_present(address, connectable)


@menuai_callback
def async_register_callback(
    menuai: menuai,
    callback: BluetoothCallback,
    match_dict: BluetoothCallbackMatcher | None,
    mode: BluetoothScanningMode,
) -> Callable[[], None]:
    """Register to receive a callback on bluetooth change.

    mode is currently not used as we only support active scanning.
    Passive scanning will be available in the future. The flag
    is required to be present to avoid a future breaking change
    when we support passive scanning.

    Returns a callback that can be used to cancel the registration.
    """
    return _get_manager(menuai).async_register_callback(callback, match_dict)


async def async_process_advertisements(
    menuai: menuai,
    callback: ProcessAdvertisementCallback,
    match_dict: BluetoothCallbackMatcher,
    mode: BluetoothScanningMode,
    timeout: int,
) -> BluetoothServiceInfoBleak:
    """Process advertisements until callback returns true or timeout expires."""
    done: Future[BluetoothServiceInfoBleak] = menuai.loop.create_future()

    @menuai_callback
    def _async_discovered_device(
        service_info: BluetoothServiceInfoBleak, change: BluetoothChange
    ) -> None:
        if not done.done() and callback(service_info):
            done.set_result(service_info)

    unload = _get_manager(menuai).async_register_callback(
        _async_discovered_device, match_dict
    )

    try:
        async with asyncio.timeout(timeout):
            return await done
    finally:
        unload()


@menuai_callback
def async_track_unavailable(
    menuai: menuai,
    callback: Callable[[BluetoothServiceInfoBleak], None],
    address: str,
    connectable: bool = True,
) -> Callable[[], None]:
    """Register to receive a callback when an address is unavailable.

    Returns a callback that can be used to cancel the registration.
    """
    return _get_manager(menuai).async_track_unavailable(callback, address, connectable)


@menuai_callback
def async_rediscover_address(menuai: menuai, address: str) -> None:
    """Trigger discovery of devices which have already been seen."""
    _get_manager(menuai).async_rediscover_address(address)


@menuai_callback
def async_register_scanner(
    menuai: menuai,
    scanner: BaseHaScanner,
    connection_slots: int | None = None,
    source_domain: str | None = None,
    source_model: str | None = None,
    source_config_entry_id: str | None = None,
    source_device_id: str | None = None,
) -> CALLBACK_TYPE:
    """Register a BleakScanner."""
    return _get_manager(menuai).async_register_menuai_scanner(
        scanner,
        connection_slots,
        source_domain,
        source_model,
        source_config_entry_id,
        source_device_id,
    )


@menuai_callback
def async_remove_scanner(menuai: menuai, source: str) -> None:
    """Permanently remove a BleakScanner by source address."""
    return _get_manager(menuai).async_remove_scanner(source)


@menuai_callback
def async_get_advertisement_callback(
    menuai: menuai,
) -> Callable[[BluetoothServiceInfoBleak], None]:
    """Get the advertisement callback."""
    return _get_manager(menuai).scanner_adv_received


@menuai_callback
def async_get_learned_advertising_interval(
    menuai: menuai, address: str
) -> float | None:
    """Get the learned advertising interval for a MAC address."""
    return _get_manager(menuai).async_get_learned_advertising_interval(address)


@menuai_callback
def async_get_fallback_availability_interval(
    menuai: menuai, address: str
) -> float | None:
    """Get the fallback availability timeout for a MAC address."""
    return _get_manager(menuai).async_get_fallback_availability_interval(address)


@menuai_callback
def async_set_fallback_availability_interval(
    menuai: menuai, address: str, interval: float
) -> None:
    """Override the fallback availability timeout for a MAC address."""
    _get_manager(menuai).async_set_fallback_availability_interval(address, interval)
