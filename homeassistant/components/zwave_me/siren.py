"""Representation of a sirenBinary."""

from typing import Any

from menuai.components.siren import SirenEntity, SirenEntityFeature
from menuai.config_entries import ConfigEntry
from menuai.core import menuai, callback
from menuai.helpers.dispatcher import async_dispatcher_connect
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, ZWaveMePlatform
from .entity import ZWaveMeEntity

DEVICE_NAME = ZWaveMePlatform.SIREN


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the siren platform."""

    @callback
    def add_new_device(new_device):
        controller = menuai.data[DOMAIN][config_entry.entry_id]
        siren = ZWaveMeSiren(controller, new_device)

        async_add_entities(
            [
                siren,
            ]
        )

    config_entry.async_on_unload(
        async_dispatcher_connect(
            menuai, f"ZWAVE_ME_NEW_{DEVICE_NAME.upper()}", add_new_device
        )
    )


class ZWaveMeSiren(ZWaveMeEntity, SirenEntity):
    """Representation of a ZWaveMe siren."""

    def __init__(self, controller, device):
        """Initialize the device."""
        super().__init__(controller, device)
        self._attr_supported_features = (
            SirenEntityFeature.TURN_ON | SirenEntityFeature.TURN_OFF
        )

    @property
    def is_on(self) -> bool:
        """Return the state of the siren."""
        return self.device.level == "on"

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        self.controller.zwave_api.send_command(self.device.id, "on")

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        self.controller.zwave_api.send_command(self.device.id, "off")
