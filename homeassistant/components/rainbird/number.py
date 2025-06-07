"""The number platform for rainbird."""

from __future__ import annotations

import logging

from pyrainbird.exceptions import RainbirdApiException, RainbirdDeviceBusyException

from menuai.components.number import NumberEntity
from menuai.const import UnitOfTime
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback
from menuai.helpers.update_coordinator import CoordinatorEntity

from .coordinator import RainbirdUpdateCoordinator
from .types import RainbirdConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    menuai: menuai,
    config_entry: RainbirdConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up entry for a Rain Bird number platform."""
    async_add_entities(
        [
            RainDelayNumber(
                config_entry.runtime_data.coordinator,
            )
        ]
    )


class RainDelayNumber(CoordinatorEntity[RainbirdUpdateCoordinator], NumberEntity):
    """A number implementation for the rain delay."""

    _attr_native_min_value = 0
    _attr_native_max_value = 14
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.DAYS
    _attr_translation_key = "rain_delay"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RainbirdUpdateCoordinator,
    ) -> None:
        """Initialize the Rain Bird sensor."""
        super().__init__(coordinator)
        if coordinator.unique_id is not None:
            self._attr_unique_id = f"{coordinator.unique_id}-rain-delay"
            self._attr_device_info = coordinator.device_info
        else:
            self._attr_name = f"{coordinator.device_name} Rain delay"

    @property
    def native_value(self) -> float | None:
        """Return the value reported by the sensor."""
        return self.coordinator.data.rain_delay

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        try:
            await self.coordinator.controller.set_rain_delay(value)
        except RainbirdDeviceBusyException as err:
            raise menuaiError(
                "Rain Bird device is busy; Wait and try again"
            ) from err
        except RainbirdApiException as err:
            raise menuaiError("Rain Bird device failure") from err
