"""Support for package tracking sensors from 17track.net."""

from __future__ import annotations

from menuai.components.sensor import SensorEntity
from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.device_registry import DeviceEntryType, DeviceInfo
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback
from menuai.helpers.typing import StateType
from menuai.helpers.update_coordinator import CoordinatorEntity

from . import SeventeenTrackCoordinator
from .const import ATTRIBUTION, DOMAIN


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up a 17Track sensor entry."""

    coordinator: SeventeenTrackCoordinator = menuai.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        SeventeenTrackSummarySensor(status, coordinator)
        for status, summary_data in coordinator.data.summary.items()
    )


class SeventeenTrackSensor(CoordinatorEntity[SeventeenTrackCoordinator], SensorEntity):
    """Define a 17Track sensor."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(self, coordinator: SeventeenTrackCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.account_id)},
            entry_type=DeviceEntryType.SERVICE,
            name="17Track",
        )


class SeventeenTrackSummarySensor(SeventeenTrackSensor):
    """Define a summary sensor."""

    _attr_native_unit_of_measurement = "packages"

    def __init__(
        self,
        status: str,
        coordinator: SeventeenTrackCoordinator,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._status = status
        self._attr_translation_key = status
        self._attr_unique_id = f"summary_{coordinator.account_id}_{status}"

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""
        return self._status in self.coordinator.data.summary

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.coordinator.data.summary[self._status]["quantity"]
