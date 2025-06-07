"""Alarm sensors for the Venstar Thermostat."""

from menuai.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .entity import VenstarEntity


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Vensar device binary_sensors based on a config entry."""
    coordinator = menuai.data[DOMAIN][config_entry.entry_id]

    if coordinator.client.alerts is None:
        return
    async_add_entities(
        VenstarBinarySensor(coordinator, config_entry, alert["name"])
        for alert in coordinator.client.alerts
    )


class VenstarBinarySensor(VenstarEntity, BinarySensorEntity):
    """Represent a Venstar alert."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator, config, alert):
        """Initialize the alert."""
        super().__init__(coordinator, config)
        self.alert = alert
        self._attr_unique_id = f"{config.entry_id}_{alert.replace(' ', '_')}"
        self._attr_name = alert

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        for alert in self._client.alerts:
            if alert["name"] == self.alert:
                return alert["active"]

        return None
