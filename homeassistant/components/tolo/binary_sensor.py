"""TOLO Sauna binary sensors."""

from menuai.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from menuai.config_entries import ConfigEntry
from menuai.const import EntityCategory
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import ToloSaunaUpdateCoordinator
from .entity import ToloSaunaCoordinatorEntity


async def async_setup_entry(
    menuai: menuai,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensors for TOLO Sauna."""
    coordinator = menuai.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            ToloFlowInBinarySensor(coordinator, entry),
            ToloFlowOutBinarySensor(coordinator, entry),
        ]
    )


class ToloFlowInBinarySensor(ToloSaunaCoordinatorEntity, BinarySensorEntity):
    """Water In Valve Sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "water_in_valve"
    _attr_device_class = BinarySensorDeviceClass.OPENING

    def __init__(
        self, coordinator: ToloSaunaUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize TOLO Water In Valve entity."""
        super().__init__(coordinator, entry)

        self._attr_unique_id = f"{entry.entry_id}_flow_in"

    @property
    def is_on(self) -> bool:
        """Return if flow in valve is open."""
        return self.coordinator.data.status.flow_in


class ToloFlowOutBinarySensor(ToloSaunaCoordinatorEntity, BinarySensorEntity):
    """Water Out Valve Sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "water_out_valve"
    _attr_device_class = BinarySensorDeviceClass.OPENING

    def __init__(
        self, coordinator: ToloSaunaUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize TOLO Water Out Valve entity."""
        super().__init__(coordinator, entry)

        self._attr_unique_id = f"{entry.entry_id}_flow_out"

    @property
    def is_on(self) -> bool:
        """Return if flow out valve is open."""
        return self.coordinator.data.status.flow_out
