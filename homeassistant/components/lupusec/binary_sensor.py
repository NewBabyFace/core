"""Support for Lupusec Security System binary sensors."""

from __future__ import annotations

from datetime import timedelta
from functools import partial
import logging

import lupupy.constants as CONST

from menuai.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DOMAIN
from .entity import LupusecBaseSensor

SCAN_INTERVAL = timedelta(seconds=2)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up a binary sensors for a Lupusec device."""

    data = menuai.data[DOMAIN][config_entry.entry_id]

    device_types = CONST.TYPE_OPENING + CONST.TYPE_SENSOR

    partial_func = partial(data.get_devices, generic_type=device_types)
    devices = await menuai.async_add_executor_job(partial_func)

    async_add_entities(
        LupusecBinarySensor(device, config_entry.entry_id) for device in devices
    )


class LupusecBinarySensor(LupusecBaseSensor, BinarySensorEntity):
    """A binary sensor implementation for Lupusec device."""

    _attr_name = None

    @property
    def is_on(self) -> bool:
        """Return True if the binary sensor is on."""
        return self._device.is_on

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        """Return the class of the binary sensor."""
        if self._device.generic_type not in (
            item.value for item in BinarySensorDeviceClass
        ):
            return None
        return self._device.generic_type
