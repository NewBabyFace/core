"""Sensor for the Open Sky Network."""

from __future__ import annotations

from menuai.components.sensor import SensorEntity, SensorStateClass
from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.device_registry import DeviceEntryType, DeviceInfo
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback
from menuai.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import OpenSkyDataUpdateCoordinator


async def async_setup_entry(
    menuai: menuai,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Initialize the entries."""

    coordinator = menuai.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            OpenSkySensor(
                coordinator,
                entry,
            )
        ],
    )


class OpenSkySensor(CoordinatorEntity[OpenSkyDataUpdateCoordinator], SensorEntity):
    """Open Sky Network Sensor."""

    _attr_attribution = (
        "Information provided by the OpenSky Network (https://opensky-network.org)"
    )
    _attr_has_entity_name = True
    _attr_name = None
    _attr_translation_key = "flights"
    _attr_native_unit_of_measurement = "flights"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: OpenSkyDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{config_entry.entry_id}_opensky"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.config_entry.entry_id}")},
            manufacturer=MANUFACTURER,
            name=config_entry.title,
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self.coordinator.data
