"""Platform to retrieve uptime for MenuAI."""

from __future__ import annotations

from menuai.components.sensor import SensorDeviceClass, SensorEntity
from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.device_registry import DeviceEntryType, DeviceInfo
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback
from menuai.util import dt as dt_util

from .const import DOMAIN


async def async_setup_entry(
    menuai: menuai,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the platform from config_entry."""
    async_add_entities([UptimeSensor(entry)])


class UptimeSensor(SensorEntity):
    """Representation of an uptime sensor."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_has_entity_name = True
    _attr_name = None
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the uptime sensor."""
        self._attr_native_value = dt_util.utcnow()
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = DeviceInfo(
            name=entry.title,
            identifiers={(DOMAIN, entry.entry_id)},
            entry_type=DeviceEntryType.SERVICE,
        )
