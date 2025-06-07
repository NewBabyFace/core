"""Support for Volvo On Call sensors."""

from __future__ import annotations

from volvooncall.dashboard import Instrument

from menuai.components.sensor import SensorEntity
from menuai.config_entries import ConfigEntry
from menuai.core import menuai, callback
from menuai.helpers.dispatcher import async_dispatcher_connect
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, VOLVO_DISCOVERY_NEW
from .coordinator import VolvoUpdateCoordinator
from .entity import VolvoEntity


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Configure sensors from a config entry created in the integrations UI."""
    coordinator: VolvoUpdateCoordinator = menuai.data[DOMAIN][config_entry.entry_id]
    volvo_data = coordinator.volvo_data

    @callback
    def async_discover_device(instruments: list[Instrument]) -> None:
        """Discover and add a discovered Volvo On Call sensor."""
        async_add_entities(
            VolvoSensor(
                coordinator,
                instrument.vehicle.vin,
                instrument.component,
                instrument.attr,
                instrument.slug_attr,
            )
            for instrument in instruments
            if instrument.component == "sensor"
        )

    async_discover_device([*volvo_data.instruments])

    config_entry.async_on_unload(
        async_dispatcher_connect(menuai, VOLVO_DISCOVERY_NEW, async_discover_device)
    )


class VolvoSensor(VolvoEntity, SensorEntity):
    """Representation of a Volvo sensor."""

    def __init__(
        self,
        coordinator: VolvoUpdateCoordinator,
        vin: str,
        component: str,
        attribute: str,
        slug_attr: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(vin, component, attribute, slug_attr, coordinator)
        self._update_value_and_unit()

    def _update_value_and_unit(self) -> None:
        self._attr_native_value = self.instrument.state
        self._attr_native_unit_of_measurement = self.instrument.unit

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_value_and_unit()
        self.async_write_ha_state()
