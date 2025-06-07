"""Support for LaMetric sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from demetriek import Device

from menuai.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from menuai.config_entries import ConfigEntry
from menuai.const import PERCENTAGE, EntityCategory
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import LaMetricDataUpdateCoordinator
from .entity import LaMetricEntity


@dataclass(frozen=True, kw_only=True)
class LaMetricSensorEntityDescription(SensorEntityDescription):
    """Class describing LaMetric sensor entities."""

    value_fn: Callable[[Device], int | None]


SENSORS = [
    LaMetricSensorEntityDescription(
        key="rssi",
        translation_key="rssi",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.wifi.rssi,
    ),
]


async def async_setup_entry(
    menuai: menuai,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up LaMetric sensor based on a config entry."""
    coordinator: LaMetricDataUpdateCoordinator = menuai.data[DOMAIN][entry.entry_id]
    async_add_entities(
        LaMetricSensorEntity(
            coordinator=coordinator,
            description=description,
        )
        for description in SENSORS
    )


class LaMetricSensorEntity(LaMetricEntity, SensorEntity):
    """Representation of a LaMetric sensor."""

    entity_description: LaMetricSensorEntityDescription

    def __init__(
        self,
        coordinator: LaMetricDataUpdateCoordinator,
        description: LaMetricSensorEntityDescription,
    ) -> None:
        """Initiate LaMetric sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.data.serial_number}-{description.key}"

    @property
    def native_value(self) -> int | None:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)
