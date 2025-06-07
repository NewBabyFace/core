"""Sensors flow for Withings."""

from __future__ import annotations

from collections.abc import Callable

from menuai.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import WithingsConfigEntry
from .const import DOMAIN
from .coordinator import WithingsBedPresenceDataUpdateCoordinator
from .entity import WithingsEntity


async def async_setup_entry(
    menuai: menuai,
    entry: WithingsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensor config entry."""
    coordinator = entry.runtime_data.bed_presence_coordinator

    ent_reg = er.async_get(menuai)

    callback: Callable[[], None] | None = None

    def _async_add_bed_presence_entity() -> None:
        """Add bed presence entity."""
        async_add_entities([WithingsBinarySensor(coordinator)])
        if callback:
            callback()

    if ent_reg.async_get_entity_id(
        Platform.BINARY_SENSOR, DOMAIN, f"withings_{entry.unique_id}_in_bed"
    ):
        _async_add_bed_presence_entity()
    else:
        callback = coordinator.async_add_listener(_async_add_bed_presence_entity)


class WithingsBinarySensor(WithingsEntity, BinarySensorEntity):
    """Implementation of a Withings sensor."""

    _attr_translation_key = "in_bed"
    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY
    coordinator: WithingsBedPresenceDataUpdateCoordinator

    def __init__(self, coordinator: WithingsBedPresenceDataUpdateCoordinator) -> None:
        """Initialize binary sensor."""
        super().__init__(coordinator, "in_bed")

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self.coordinator.in_bed
