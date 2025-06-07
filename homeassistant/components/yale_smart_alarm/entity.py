"""Base class for yale_smart_alarm entity."""

from yalesmartalarmclient import YaleLock

from menuai.const import CONF_USERNAME
from menuai.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from menuai.helpers.entity import Entity
from menuai.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import YaleDataUpdateCoordinator


class YaleEntity(CoordinatorEntity[YaleDataUpdateCoordinator]):
    """Base implementation for Yale device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: YaleDataUpdateCoordinator, data: dict) -> None:
        """Initialize an Yale device."""
        super().__init__(coordinator)
        self._attr_unique_id: str = data["address"]
        self._attr_device_info: DeviceInfo = DeviceInfo(
            name=data["name"],
            manufacturer=MANUFACTURER,
            model=MODEL,
            identifiers={(DOMAIN, data["address"])},
            via_device=(DOMAIN, coordinator.config_entry.data[CONF_USERNAME]),
        )


class YaleLockEntity(CoordinatorEntity[YaleDataUpdateCoordinator]):
    """Base implementation for Yale lock device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: YaleDataUpdateCoordinator, lock: YaleLock) -> None:
        """Initialize an Yale device."""
        super().__init__(coordinator)
        self._attr_unique_id: str = lock.sid()
        self._attr_device_info = DeviceInfo(
            name=lock.name,
            manufacturer=MANUFACTURER,
            model=MODEL,
            identifiers={(DOMAIN, lock.sid())},
            via_device=(DOMAIN, coordinator.config_entry.data[CONF_USERNAME]),
        )
        self.lock_data = lock


class YaleAlarmEntity(CoordinatorEntity[YaleDataUpdateCoordinator], Entity):
    """Base implementation for Yale Alarm device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: YaleDataUpdateCoordinator) -> None:
        """Initialize an Yale device."""
        super().__init__(coordinator)
        panel_info = coordinator.data["panel_info"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.data[CONF_USERNAME])},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=coordinator.config_entry.title,
            connections={(CONNECTION_NETWORK_MAC, panel_info["mac"])},
            sw_version=panel_info["version"],
        )
