"""Support for openexchangerates.org exchange rates service."""

from __future__ import annotations

from menuai.components.sensor import SensorEntity
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_QUOTE
from menuai.core import menuai
from menuai.helpers.device_registry import DeviceEntryType, DeviceInfo
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback
from menuai.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OpenexchangeratesCoordinator

ATTRIBUTION = "Data provided by openexchangerates.org"


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Open Exchange Rates sensor."""
    quote: str = config_entry.data.get(CONF_QUOTE, "EUR")
    coordinator = menuai.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        OpenexchangeratesSensor(
            config_entry, coordinator, rate_quote, rate_quote == quote
        )
        for rate_quote in coordinator.data.rates
    )


class OpenexchangeratesSensor(
    CoordinatorEntity[OpenexchangeratesCoordinator], SensorEntity
):
    """Representation of an Open Exchange Rates sensor."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        config_entry: ConfigEntry,
        coordinator: OpenexchangeratesCoordinator,
        quote: str,
        enabled: bool,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, config_entry.entry_id)},
            manufacturer="Open Exchange Rates",
            name=f"Open Exchange Rates {coordinator.base}",
        )
        self._attr_entity_registry_enabled_default = enabled
        self._attr_name = quote
        self._attr_native_unit_of_measurement = quote
        self._attr_unique_id = f"{config_entry.entry_id}_{quote}"
        self._quote = quote

    @property
    def native_value(self) -> float:
        """Return the state of the sensor."""
        return self.coordinator.data.rates[self._quote]
