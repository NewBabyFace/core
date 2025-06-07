"""Sensor platform for menuai.io addons."""

from __future__ import annotations

from menuai.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from menuai.config_entries import ConfigEntry
from menuai.const import PERCENTAGE, EntityCategory, UnitOfInformation
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    ADDONS_COORDINATOR,
    ATTR_CPU_PERCENT,
    ATTR_MEMORY_PERCENT,
    ATTR_VERSION,
    ATTR_VERSION_LATEST,
    DATA_KEY_ADDONS,
    DATA_KEY_CORE,
    DATA_KEY_HOST,
    DATA_KEY_OS,
    DATA_KEY_SUPERVISOR,
)
from .entity import (
    menuaiioAddonEntity,
    menuaiioCoreEntity,
    menuaiioHostEntity,
    menuaiioOSEntity,
    menuaiioSupervisorEntity,
)

COMMON_ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        entity_registry_enabled_default=False,
        key=ATTR_VERSION,
        translation_key="version",
    ),
    SensorEntityDescription(
        entity_registry_enabled_default=False,
        key=ATTR_VERSION_LATEST,
        translation_key="version_latest",
    ),
)

STATS_ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        entity_registry_enabled_default=False,
        key=ATTR_CPU_PERCENT,
        translation_key="cpu_percent",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        entity_registry_enabled_default=False,
        key=ATTR_MEMORY_PERCENT,
        translation_key="memory_percent",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)

ADDON_ENTITY_DESCRIPTIONS = COMMON_ENTITY_DESCRIPTIONS + STATS_ENTITY_DESCRIPTIONS
CORE_ENTITY_DESCRIPTIONS = STATS_ENTITY_DESCRIPTIONS
OS_ENTITY_DESCRIPTIONS = COMMON_ENTITY_DESCRIPTIONS
SUPERVISOR_ENTITY_DESCRIPTIONS = STATS_ENTITY_DESCRIPTIONS

HOST_ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        entity_registry_enabled_default=False,
        key="agent_version",
        translation_key="agent_version",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        entity_registry_enabled_default=False,
        key="apparmor_version",
        translation_key="apparmor_version",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        entity_registry_enabled_default=False,
        key="disk_total",
        translation_key="disk_total",
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        entity_registry_enabled_default=False,
        key="disk_used",
        translation_key="disk_used",
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        entity_registry_enabled_default=False,
        key="disk_free",
        translation_key="disk_free",
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Sensor set up for menuai.io config entry."""
    coordinator = menuai.data[ADDONS_COORDINATOR]

    entities: list[
        menuaiioOSSensor | menuaiioAddonSensor | CoreSensor | SupervisorSensor | HostSensor
    ] = [
        menuaiioAddonSensor(
            addon=addon,
            coordinator=coordinator,
            entity_description=entity_description,
        )
        for addon in coordinator.data[DATA_KEY_ADDONS].values()
        for entity_description in ADDON_ENTITY_DESCRIPTIONS
    ]

    entities.extend(
        CoreSensor(
            coordinator=coordinator,
            entity_description=entity_description,
        )
        for entity_description in CORE_ENTITY_DESCRIPTIONS
    )

    entities.extend(
        SupervisorSensor(
            coordinator=coordinator,
            entity_description=entity_description,
        )
        for entity_description in SUPERVISOR_ENTITY_DESCRIPTIONS
    )

    entities.extend(
        HostSensor(
            coordinator=coordinator,
            entity_description=entity_description,
        )
        for entity_description in HOST_ENTITY_DESCRIPTIONS
    )

    if coordinator.is_menuai_os:
        entities.extend(
            menuaiioOSSensor(
                coordinator=coordinator,
                entity_description=entity_description,
            )
            for entity_description in OS_ENTITY_DESCRIPTIONS
        )

    async_add_entities(entities)


class menuaiioAddonSensor(menuaiioAddonEntity, SensorEntity):
    """Sensor to track a menuai.io add-on attribute."""

    @property
    def native_value(self) -> str:
        """Return native value of entity."""
        return self.coordinator.data[DATA_KEY_ADDONS][self._addon_slug][
            self.entity_description.key
        ]


class menuaiioOSSensor(menuaiioOSEntity, SensorEntity):
    """Sensor to track a menuai.io add-on attribute."""

    @property
    def native_value(self) -> str:
        """Return native value of entity."""
        return self.coordinator.data[DATA_KEY_OS][self.entity_description.key]


class CoreSensor(menuaiioCoreEntity, SensorEntity):
    """Sensor to track a core attribute."""

    @property
    def native_value(self) -> str:
        """Return native value of entity."""
        return self.coordinator.data[DATA_KEY_CORE][self.entity_description.key]


class SupervisorSensor(menuaiioSupervisorEntity, SensorEntity):
    """Sensor to track a supervisor attribute."""

    @property
    def native_value(self) -> str:
        """Return native value of entity."""
        return self.coordinator.data[DATA_KEY_SUPERVISOR][self.entity_description.key]


class HostSensor(menuaiioHostEntity, SensorEntity):
    """Sensor to track a host attribute."""

    @property
    def native_value(self) -> str:
        """Return native value of entity."""
        return self.coordinator.data[DATA_KEY_HOST][self.entity_description.key]
