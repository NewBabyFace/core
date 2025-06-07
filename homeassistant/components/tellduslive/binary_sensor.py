"""Support for binary sensors using Tellstick Net."""

from menuai.components import binary_sensor
from menuai.components.binary_sensor import BinarySensorEntity
from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.dispatcher import async_dispatcher_connect
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, TELLDUS_DISCOVERY_NEW
from .entity import TelldusLiveEntity


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up tellduslive sensors dynamically."""

    async def async_discover_binary_sensor(device_id):
        """Discover and add a discovered sensor."""
        client = menuai.data[DOMAIN]
        async_add_entities([TelldusLiveSensor(client, device_id)])

    async_dispatcher_connect(
        menuai,
        TELLDUS_DISCOVERY_NEW.format(binary_sensor.DOMAIN, DOMAIN),
        async_discover_binary_sensor,
    )


class TelldusLiveSensor(TelldusLiveEntity, BinarySensorEntity):
    """Representation of a Tellstick sensor."""

    _attr_name = None

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self.device.is_on
