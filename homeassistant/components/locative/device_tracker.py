"""Support for the Locative platform."""

from menuai.components.device_tracker import TrackerEntity
from menuai.config_entries import ConfigEntry
from menuai.core import menuai, callback
from menuai.helpers.dispatcher import async_dispatcher_connect
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DOMAIN, TRACKER_UPDATE


async def async_setup_entry(
    menuai: menuai,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Configure a dispatcher connection based on a config entry."""

    @callback
    def _receive_data(device, location, location_name):
        """Receive set location."""
        if device in menuai.data[DOMAIN]["devices"]:
            return

        menuai.data[DOMAIN]["devices"].add(device)

        async_add_entities([LocativeEntity(device, location, location_name)])

    menuai.data[DOMAIN]["unsub_device_tracker"][entry.entry_id] = (
        async_dispatcher_connect(menuai, TRACKER_UPDATE, _receive_data)
    )


class LocativeEntity(TrackerEntity):
    """Represent a tracked device."""

    def __init__(self, device, location, location_name):
        """Set up Locative entity."""
        self._name = device
        self._attr_latitude = location[0]
        self._attr_longitude = location[1]
        self._attr_location_name = location_name
        self._unsub_dispatcher = None

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    async def async_added_to_menuai(self) -> None:
        """Register state update callback."""
        self._unsub_dispatcher = async_dispatcher_connect(
            self.menuai, TRACKER_UPDATE, self._async_receive_data
        )

    async def async_will_remove_from_menuai(self) -> None:
        """Clean up after entity before removal."""
        self._unsub_dispatcher()

    @callback
    def _async_receive_data(self, device, location, location_name):
        """Update device data."""
        if device != self._name:
            return
        self._attr_location_name = location_name
        self._attr_latitude = location[0]
        self._attr_longitude = location[1]
        self.async_write_ha_state()
