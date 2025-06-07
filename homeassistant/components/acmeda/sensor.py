"""Support for Acmeda Roller Blind Batteries."""

from __future__ import annotations

from menuai.components.sensor import SensorDeviceClass, SensorEntity
from menuai.const import PERCENTAGE
from menuai.core import menuai, callback
from menuai.helpers.dispatcher import async_dispatcher_connect
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AcmedaConfigEntry
from .const import ACMEDA_HUB_UPDATE
from .entity import AcmedaEntity
from .helpers import async_add_acmeda_entities


async def async_setup_entry(
    menuai: menuai,
    config_entry: AcmedaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Acmeda Rollers from a config entry."""
    hub = config_entry.runtime_data

    current: set[int] = set()

    @callback
    def async_add_acmeda_sensors() -> None:
        async_add_acmeda_entities(
            menuai, AcmedaBattery, config_entry, current, async_add_entities
        )

    hub.cleanup_callbacks.append(
        async_dispatcher_connect(
            menuai,
            ACMEDA_HUB_UPDATE.format(config_entry.entry_id),
            async_add_acmeda_sensors,
        )
    )


class AcmedaBattery(AcmedaEntity, SensorEntity):
    """Representation of an Acmeda cover sensor."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self) -> float | int | None:
        """Return the state of the device."""
        return self.roller.battery  # type: ignore[no-any-return]
