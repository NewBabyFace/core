"""Support for the Rainforest Eagle energy monitor."""

from __future__ import annotations

from menuai.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from menuai.config_entries import ConfigEntry
from menuai.const import UnitOfEnergy, UnitOfPower
from menuai.core import menuai
from menuai.helpers.device_registry import DeviceInfo
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback
from menuai.helpers.typing import StateType
from menuai.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EagleDataCoordinator

SENSORS = (
    SensorEntityDescription(
        key="zigbee:InstantaneousDemand",
        translation_key="power_demand",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="zigbee:CurrentSummationDelivered",
        translation_key="total_energy_delivered",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="zigbee:CurrentSummationReceived",
        translation_key="total_energy_received",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
)


async def async_setup_entry(
    menuai: menuai,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up a config entry."""
    coordinator = menuai.data[DOMAIN][entry.entry_id]
    entities = [EagleSensor(coordinator, description) for description in SENSORS]

    if coordinator.data.get("zigbee:Price") not in (None, "invalid"):
        entities.append(
            EagleSensor(
                coordinator,
                SensorEntityDescription(
                    key="zigbee:Price",
                    translation_key="energy_price",
                    native_unit_of_measurement=f"{coordinator.data['zigbee:PriceCurrency']}/{UnitOfEnergy.KILO_WATT_HOUR}",
                    state_class=SensorStateClass.MEASUREMENT,
                ),
            )
        )

    async_add_entities(entities)


class EagleSensor(CoordinatorEntity[EagleDataCoordinator], SensorEntity):
    """Implementation of the Rainforest Eagle sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entity_description):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = f"{coordinator.cloud_id}-${coordinator.hardware_address}-{entity_description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.cloud_id)},
            manufacturer="Rainforest Automation",
            model=coordinator.model,
            name=coordinator.model,
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and self.coordinator.is_connected

    @property
    def native_value(self) -> StateType:
        """Return native value of the sensor."""
        return self.coordinator.data.get(self.entity_description.key)
