"""Representation of Idasen Desk sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from menuai.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from menuai.const import UnitOfLength
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import IdasenDeskConfigEntry, IdasenDeskCoordinator
from .entity import IdasenDeskEntity


@dataclass(frozen=True, kw_only=True)
class IdasenDeskSensorDescription(SensorEntityDescription):
    """Class describing IdasenDesk sensor entities."""

    value_fn: Callable[[IdasenDeskCoordinator], float | None]


SENSORS = (
    IdasenDeskSensorDescription(
        key="height",
        translation_key="height",
        native_unit_of_measurement=UnitOfLength.METERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        suggested_display_precision=3,
        value_fn=lambda coordinator: coordinator.desk.height,
    ),
)


async def async_setup_entry(
    menuai: menuai,
    entry: IdasenDeskConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Idasen Desk sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        IdasenDeskSensor(coordinator, sensor_description)
        for sensor_description in SENSORS
    )


class IdasenDeskSensor(IdasenDeskEntity, SensorEntity):
    """IdasenDesk sensor."""

    entity_description: IdasenDeskSensorDescription

    def __init__(
        self,
        coordinator: IdasenDeskCoordinator,
        description: IdasenDeskSensorDescription,
    ) -> None:
        """Initialize the IdasenDesk sensor entity."""
        super().__init__(f"{description.key}-{coordinator.address}", coordinator)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        """Return the value reported by the sensor."""
        return self.entity_description.value_fn(self.coordinator)
