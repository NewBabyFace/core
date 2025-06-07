"""Support for the ZHA platform."""

from __future__ import annotations

import functools

from menuai.components.device_tracker import ScannerEntity
from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers.device_registry import DeviceInfo
from menuai.helpers.dispatcher import async_dispatcher_connect
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import ZHAEntity
from .helpers import (
    SIGNAL_ADD_ENTITIES,
    async_add_entities as zha_async_add_entities,
    get_zha_data,
)


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Zigbee Home Automation device tracker from config entry."""
    zha_data = get_zha_data(menuai)
    entities_to_create = zha_data.platforms[Platform.DEVICE_TRACKER]

    unsub = async_dispatcher_connect(
        menuai,
        SIGNAL_ADD_ENTITIES,
        functools.partial(
            zha_async_add_entities,
            async_add_entities,
            ZHADeviceScannerEntity,
            entities_to_create,
        ),
    )
    config_entry.async_on_unload(unsub)


class ZHADeviceScannerEntity(ScannerEntity, ZHAEntity):
    """Represent a tracked device."""

    _attr_should_poll = True  # BaseZhaEntity defaults to False
    _attr_name: str = "Device scanner"

    @property
    def is_connected(self) -> bool:
        """Return true if the device is connected to the network."""
        return self.entity_data.entity.is_connected

    @property
    def battery_level(self) -> int | None:
        """Return the battery level of the device.

        Percentage from 0-100.
        """
        return self.entity_data.entity.battery_level

    @property  # type: ignore[misc]
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        # We opt ZHA device tracker back into overriding this method because
        # it doesn't track IP-based devices.
        return ZHAEntity.device_info.__get__(self)

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        # Call Super because ScannerEntity overrode it.
        return ZHAEntity.unique_id.__get__(self)
