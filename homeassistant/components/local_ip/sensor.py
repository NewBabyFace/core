"""Sensor platform for local_ip."""

from menuai.components.network import async_get_source_ip
from menuai.components.sensor import SensorEntity
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_NAME
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import SENSOR


async def async_setup_entry(
    menuai: menuai,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the platform from config_entry."""
    name = entry.data.get(CONF_NAME) or "Local IP"
    async_add_entities([IPSensor(name)], True)


class IPSensor(SensorEntity):
    """A simple sensor."""

    _attr_unique_id = SENSOR
    _attr_translation_key = "local_ip"

    def __init__(self, name: str) -> None:
        """Initialize the sensor."""
        self._attr_name = name

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        self._attr_native_value = await async_get_source_ip(self.menuai)
