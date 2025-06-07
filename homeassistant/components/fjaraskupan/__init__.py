"""The Fjäråskupan integration."""

from __future__ import annotations

from collections.abc import Callable
import logging

from fjaraskupan import Device

from menuai.components.bluetooth import (
    BluetoothCallbackMatcher,
    BluetoothChange,
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
    async_rediscover_address,
    async_register_callback,
)
from menuai.const import Platform
from menuai.core import menuai, callback
from menuai.helpers import device_registry as dr
from menuai.helpers.device_registry import DeviceInfo
from menuai.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from menuai.helpers.entity import Entity
from menuai.helpers.entity_platform import AddEntitiesCallback

from .const import DISPATCH_DETECTION, DOMAIN
from .coordinator import FjaraskupanConfigEntry, FjaraskupanCoordinator

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.FAN,
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.SENSOR,
]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: FjaraskupanConfigEntry) -> bool:
    """Set up Fjäråskupan from a config entry."""

    entry.runtime_data = {}

    def detection_callback(
        service_info: BluetoothServiceInfoBleak, change: BluetoothChange
    ) -> None:
        if change != BluetoothChange.ADVERTISEMENT:
            return
        if data := entry.runtime_data.get(service_info.address):
            _LOGGER.debug("Update: %s", service_info)
            data.detection_callback(service_info)
        else:
            _LOGGER.debug("Detected: %s", service_info)

            device = Device(service_info.device.address)
            device_info = DeviceInfo(
                connections={(dr.CONNECTION_BLUETOOTH, service_info.address)},
                identifiers={(DOMAIN, service_info.address)},
                manufacturer="Fjäråskupan",
                name="Fjäråskupan",
            )

            coordinator: FjaraskupanCoordinator = FjaraskupanCoordinator(
                menuai, entry, device, device_info
            )
            coordinator.detection_callback(service_info)

            entry.runtime_data[service_info.address] = coordinator
            async_dispatcher_send(
                menuai, f"{DISPATCH_DETECTION}.{entry.entry_id}", coordinator
            )

    entry.async_on_unload(
        async_register_callback(
            menuai,
            detection_callback,
            BluetoothCallbackMatcher(
                manufacturer_id=20296,
                manufacturer_data_start=[79, 68, 70, 74, 65, 82],
                connectable=False,
            ),
            BluetoothScanningMode.ACTIVE,
        )
    )

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


@callback
def async_setup_entry_platform(
    menuai: menuai,
    entry: FjaraskupanConfigEntry,
    async_add_entities: AddEntitiesCallback,
    constructor: Callable[[FjaraskupanCoordinator], list[Entity]],
) -> None:
    """Set up a platform with added entities."""

    async_add_entities(
        entity
        for coordinator in entry.runtime_data.values()
        for entity in constructor(coordinator)
    )

    @callback
    def _detection(coordinator: FjaraskupanCoordinator) -> None:
        async_add_entities(constructor(coordinator))

    entry.async_on_unload(
        async_dispatcher_connect(
            menuai, f"{DISPATCH_DETECTION}.{entry.entry_id}", _detection
        )
    )


async def async_unload_entry(
    menuai: menuai, entry: FjaraskupanConfigEntry
) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        for device_entry in dr.async_entries_for_config_entry(
            dr.async_get(menuai), entry.entry_id
        ):
            for conn in device_entry.connections:
                if conn[0] == dr.CONNECTION_BLUETOOTH:
                    async_rediscover_address(menuai, conn[1])

    return unload_ok
