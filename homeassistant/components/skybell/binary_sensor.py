"""Binary sensor support for the Skybell HD Doorbell."""

from __future__ import annotations

from aioskybell.helpers import const as CONST

from menuai.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from menuai.config_entries import ConfigEntry
from menuai.core import menuai, callback
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DOMAIN
from .coordinator import SkybellDataUpdateCoordinator
from .entity import SkybellEntity

BINARY_SENSOR_TYPES: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key="button",
        translation_key="button",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
    ),
    BinarySensorEntityDescription(
        key="motion",
        device_class=BinarySensorDeviceClass.MOTION,
    ),
)


async def async_setup_entry(
    menuai: menuai,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Skybell binary sensor."""
    async_add_entities(
        SkybellBinarySensor(coordinator, sensor)
        for sensor in BINARY_SENSOR_TYPES
        for coordinator in menuai.data[DOMAIN][entry.entry_id]
    )


class SkybellBinarySensor(SkybellEntity, BinarySensorEntity):
    """A binary sensor implementation for Skybell devices."""

    def __init__(
        self,
        coordinator: SkybellDataUpdateCoordinator,
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize a binary sensor for a Skybell device."""
        super().__init__(coordinator, description)
        self._event: dict[str, str] = {}

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        event = self._device.latest(self.entity_description.key)
        self._attr_is_on = bool(event.get(CONST.ID) != self._event.get(CONST.ID))
        self._event = event
        super()._handle_coordinator_update()
