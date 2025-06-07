"""WiZ integration binary sensor platform."""

from __future__ import annotations

from collections.abc import Callable

from pywizlight.bulb import PIR_SOURCE

from menuai.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from menuai.const import Platform
from menuai.core import menuai, callback
from menuai.helpers import entity_registry as er
from menuai.helpers.dispatcher import async_dispatcher_connect
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import WizConfigEntry
from .const import DOMAIN, SIGNAL_WIZ_PIR
from .entity import WizEntity
from .models import WizData

OCCUPANCY_UNIQUE_ID = "{}_occupancy"


async def async_setup_entry(
    menuai: menuai,
    entry: WizConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the WiZ binary sensor platform."""
    mac = entry.runtime_data.bulb.mac

    if er.async_get(menuai).async_get_entity_id(
        Platform.BINARY_SENSOR, DOMAIN, OCCUPANCY_UNIQUE_ID.format(mac)
    ):
        async_add_entities([WizOccupancyEntity(entry.runtime_data, entry.title)])
        return

    cancel_dispatcher: Callable[[], None] | None = None

    @callback
    def _async_add_occupancy_sensor() -> None:
        nonlocal cancel_dispatcher
        assert cancel_dispatcher is not None
        cancel_dispatcher()
        cancel_dispatcher = None
        async_add_entities([WizOccupancyEntity(entry.runtime_data, entry.title)])

    cancel_dispatcher = async_dispatcher_connect(
        menuai, SIGNAL_WIZ_PIR.format(mac), _async_add_occupancy_sensor
    )

    @callback
    def _async_cancel_dispatcher() -> None:
        nonlocal cancel_dispatcher
        if cancel_dispatcher is not None:
            cancel_dispatcher()
            cancel_dispatcher = None

    entry.async_on_unload(_async_cancel_dispatcher)


class WizOccupancyEntity(WizEntity, BinarySensorEntity):
    """Representation of WiZ Occupancy sensor."""

    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY

    def __init__(self, wiz_data: WizData, name: str) -> None:
        """Initialize an WiZ device."""
        super().__init__(wiz_data, name)
        self._attr_unique_id = OCCUPANCY_UNIQUE_ID.format(self._device.mac)
        self._async_update_attrs()

    @callback
    def _async_update_attrs(self) -> None:
        """Handle updating _attr values."""
        if self._device.state.get_source() == PIR_SOURCE:
            self._attr_is_on = self._device.status
