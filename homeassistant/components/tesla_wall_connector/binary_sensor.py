"""Binary Sensors for Tesla Wall Connector."""

from dataclasses import dataclass
import logging

from menuai.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from menuai.config_entries import ConfigEntry
from menuai.const import EntityCategory
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import WallConnectorData
from .const import DOMAIN, WALLCONNECTOR_DATA_VITALS
from .entity import WallConnectorEntity, WallConnectorLambdaValueGetterMixin

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class WallConnectorBinarySensorDescription(
    BinarySensorEntityDescription, WallConnectorLambdaValueGetterMixin
):
    """Binary Sensor entity description."""


WALL_CONNECTOR_SENSORS = [
    WallConnectorBinarySensorDescription(
        key="vehicle_connected",
        translation_key="vehicle_connected",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data[WALLCONNECTOR_DATA_VITALS].vehicle_connected,
        device_class=BinarySensorDeviceClass.PLUG,
    ),
    WallConnectorBinarySensorDescription(
        key="contactor_closed",
        translation_key="contactor_closed",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data[WALLCONNECTOR_DATA_VITALS].contactor_closed,
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
    ),
]


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create the Wall Connector sensor devices."""
    wall_connector_data = menuai.data[DOMAIN][config_entry.entry_id]

    all_entities = [
        WallConnectorBinarySensorEntity(wall_connector_data, description)
        for description in WALL_CONNECTOR_SENSORS
    ]

    async_add_entities(all_entities)


class WallConnectorBinarySensorEntity(WallConnectorEntity, BinarySensorEntity):
    """Wall Connector Sensor Entity."""

    def __init__(
        self,
        wall_connectord_data: WallConnectorData,
        description: WallConnectorBinarySensorDescription,
    ) -> None:
        """Initialize WallConnectorBinarySensorEntity."""
        self.entity_description = description
        super().__init__(wall_connectord_data)

    @property
    def is_on(self):
        """Return the state of the sensor."""

        return self.entity_description.value_fn(self.coordinator.data)
