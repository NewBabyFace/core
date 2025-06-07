"""WeatherKit sensors."""

from menuai.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from menuai.config_entries import ConfigEntry
from menuai.const import UnitOfVolumetricFlux
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback
from menuai.helpers.typing import StateType
from menuai.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_CURRENT_WEATHER, DOMAIN
from .coordinator import WeatherKitDataUpdateCoordinator
from .entity import WeatherKitEntity

SENSORS = (
    SensorEntityDescription(
        key="precipitationIntensity",
        device_class=SensorDeviceClass.PRECIPITATION_INTENSITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
    ),
    SensorEntityDescription(
        key="pressureTrend",
        device_class=SensorDeviceClass.ENUM,
        options=["rising", "falling", "steady"],
        translation_key="pressure_trend",
    ),
)


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add sensor entities from a config_entry."""
    coordinator: WeatherKitDataUpdateCoordinator = menuai.data[DOMAIN][
        config_entry.entry_id
    ]

    async_add_entities(
        WeatherKitSensor(coordinator, description) for description in SENSORS
    )


class WeatherKitSensor(
    CoordinatorEntity[WeatherKitDataUpdateCoordinator], WeatherKitEntity, SensorEntity
):
    """WeatherKit sensor entity."""

    def __init__(
        self,
        coordinator: WeatherKitDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        WeatherKitEntity.__init__(
            self, coordinator, unique_id_suffix=entity_description.key
        )
        self.entity_description = entity_description

    @property
    def native_value(self) -> StateType:
        """Return native value from coordinator current weather."""
        return self.coordinator.data[ATTR_CURRENT_WEATHER][self.entity_description.key]
