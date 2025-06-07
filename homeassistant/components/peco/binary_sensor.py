"""Binary sensor for PECO outage counter."""

from __future__ import annotations

from typing import Final

from menuai.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback
from menuai.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN

PARALLEL_UPDATES: Final = 0


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensor for PECO."""
    if "smart_meter" not in menuai.data[DOMAIN][config_entry.entry_id]:
        return
    coordinator: DataUpdateCoordinator[bool] = menuai.data[DOMAIN][config_entry.entry_id][
        "smart_meter"
    ]

    async_add_entities(
        [PecoBinarySensor(coordinator, phone_number=config_entry.data["phone_number"])]
    )


class PecoBinarySensor(
    CoordinatorEntity[DataUpdateCoordinator[bool]], BinarySensorEntity
):
    """Binary sensor for PECO outage counter."""

    _attr_icon = "mdi:gauge"
    _attr_device_class = BinarySensorDeviceClass.POWER
    _attr_name = "Meter Status"

    def __init__(
        self, coordinator: DataUpdateCoordinator[bool], phone_number: str
    ) -> None:
        """Initialize binary sensor for PECO."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{phone_number}"

    @property
    def is_on(self) -> bool:
        """Return if the meter has power."""
        return self.coordinator.data
