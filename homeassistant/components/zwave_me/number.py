"""Representation of a switchMultilevel."""

from menuai.components.number import NumberEntity
from menuai.config_entries import ConfigEntry
from menuai.core import menuai, callback
from menuai.helpers.dispatcher import async_dispatcher_connect
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, ZWaveMePlatform
from .entity import ZWaveMeEntity

DEVICE_NAME = ZWaveMePlatform.NUMBER


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the number platform."""

    @callback
    def add_new_device(new_device):
        controller = menuai.data[DOMAIN][config_entry.entry_id]
        switch = ZWaveMeNumber(controller, new_device)

        async_add_entities(
            [
                switch,
            ]
        )

    config_entry.async_on_unload(
        async_dispatcher_connect(
            menuai, f"ZWAVE_ME_NEW_{DEVICE_NAME.upper()}", add_new_device
        )
    )


class ZWaveMeNumber(ZWaveMeEntity, NumberEntity):
    """Representation of a ZWaveMe Multilevel Switch."""

    @property
    def native_value(self) -> float:
        """Return the unit of measurement."""
        if self.device.level == 99:  # Scale max value
            return 100
        return self.device.level

    def set_native_value(self, value: float) -> None:
        """Update the current value."""
        self.controller.zwave_api.send_command(
            self.device.id, f"exact?level={round(value)!s}"
        )
