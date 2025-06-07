"""Support for Vallox ventilation unit binary sensors."""

from __future__ import annotations

from dataclasses import dataclass

from menuai.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from menuai.config_entries import ConfigEntry
from menuai.const import EntityCategory
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import ValloxDataUpdateCoordinator
from .entity import ValloxEntity


class ValloxBinarySensorEntity(ValloxEntity, BinarySensorEntity):
    """Representation of a Vallox binary sensor."""

    entity_description: ValloxBinarySensorEntityDescription
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        name: str,
        coordinator: ValloxDataUpdateCoordinator,
        description: ValloxBinarySensorEntityDescription,
    ) -> None:
        """Initialize the Vallox binary sensor."""
        super().__init__(name, coordinator)

        self.entity_description = description

        self._attr_unique_id = f"{self._device_uuid}-{description.key}"

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self.coordinator.data.get(self.entity_description.metric_key) == 1


@dataclass(frozen=True, kw_only=True)
class ValloxBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes Vallox binary sensor entity."""

    metric_key: str


BINARY_SENSOR_ENTITIES: tuple[ValloxBinarySensorEntityDescription, ...] = (
    ValloxBinarySensorEntityDescription(
        key="post_heater",
        translation_key="post_heater",
        metric_key="A_CYC_IO_HEATER",
    ),
)


async def async_setup_entry(
    menuai: menuai,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors."""

    data = menuai.data[DOMAIN][entry.entry_id]

    async_add_entities(
        ValloxBinarySensorEntity(data["name"], data["coordinator"], description)
        for description in BINARY_SENSOR_ENTITIES
    )
