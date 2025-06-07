"""Support for Tellstick switches using Tellstick Net."""

from typing import Any

from menuai.components import switch
from menuai.components.switch import SwitchEntity
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

    async def async_discover_switch(device_id):
        """Discover and add a discovered sensor."""
        client = menuai.data[DOMAIN]
        async_add_entities([TelldusLiveSwitch(client, device_id)])

    async_dispatcher_connect(
        menuai,
        TELLDUS_DISCOVERY_NEW.format(switch.DOMAIN, DOMAIN),
        async_discover_switch,
    )


class TelldusLiveSwitch(TelldusLiveEntity, SwitchEntity):
    """Representation of a Tellstick switch."""

    _attr_name = None

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self.device.is_on

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        self.device.turn_on()
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        self.device.turn_off()
        self.schedule_update_ha_state()
