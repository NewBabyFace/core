"""Support for Fast.com internet speed testing sensor."""

from __future__ import annotations

from menuai.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from menuai.const import UnitOfDataRate
from menuai.core import menuai
from menuai.helpers.device_registry import DeviceEntryType, DeviceInfo
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback
from menuai.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FastdotcomConfigEntry, FastdotcomDataUpdateCoordinator


async def async_setup_entry(
    menuai: menuai,
    entry: FastdotcomConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Fast.com sensor."""
    async_add_entities([SpeedtestSensor(entry.entry_id, entry.runtime_data)])


class SpeedtestSensor(CoordinatorEntity[FastdotcomDataUpdateCoordinator], SensorEntity):
    """Implementation of a Fast.com sensor."""

    _attr_translation_key = "download"
    _attr_device_class = SensorDeviceClass.DATA_RATE
    _attr_native_unit_of_measurement = UnitOfDataRate.MEGABITS_PER_SECOND
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(
        self, entry_id: str, coordinator: FastdotcomDataUpdateCoordinator
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://www.fast.com",
        )

    @property
    def native_value(
        self,
    ) -> float:
        """Return the state of the sensor."""
        return self.coordinator.data
