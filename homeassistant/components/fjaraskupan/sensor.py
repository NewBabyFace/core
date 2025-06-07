"""Support for sensors."""

from __future__ import annotations

from fjaraskupan import Device

from menuai.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from menuai.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT, EntityCategory
from menuai.core import menuai
from menuai.helpers.device_registry import DeviceInfo
from menuai.helpers.entity import Entity
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback
from menuai.helpers.typing import StateType
from menuai.helpers.update_coordinator import CoordinatorEntity

from . import async_setup_entry_platform
from .coordinator import FjaraskupanConfigEntry, FjaraskupanCoordinator


async def async_setup_entry(
    menuai: menuai,
    config_entry: FjaraskupanConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors dynamically through discovery."""

    def _constructor(coordinator: FjaraskupanCoordinator) -> list[Entity]:
        return [RssiSensor(coordinator, coordinator.device, coordinator.device_info)]

    async_setup_entry_platform(menuai, config_entry, async_add_entities, _constructor)


class RssiSensor(CoordinatorEntity[FjaraskupanCoordinator], SensorEntity):
    """Sensor device."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_entity_registry_enabled_default = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: FjaraskupanCoordinator,
        device: Device,
        device_info: DeviceInfo,
    ) -> None:
        """Init sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{device.address}-signal-strength"
        self._attr_device_info = device_info

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""
        if data := self.coordinator.data:
            return data.rssi
        return None
