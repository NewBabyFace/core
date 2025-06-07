"""Support for Aurora Forecast binary sensor."""

from __future__ import annotations

from menuai.components.binary_sensor import BinarySensorEntity
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AuroraConfigEntry
from .entity import AuroraEntity


async def async_setup_entry(
    menuai: menuai,
    entry: AuroraConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary_sensor platform."""
    async_add_entities(
        [
            AuroraSensor(
                coordinator=entry.runtime_data,
                translation_key="visibility_alert",
            )
        ]
    )


class AuroraSensor(AuroraEntity, BinarySensorEntity):
    """Implementation of an aurora sensor."""

    @property
    def is_on(self) -> bool:
        """Return true if aurora is visible."""
        return self.coordinator.data > self.coordinator.threshold
