"""Support for Fibaro switches."""

from __future__ import annotations

from typing import Any

from pyfibaro.fibaro_device import DeviceModel

from menuai.components.switch import ENTITY_ID_FORMAT, SwitchEntity
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import FibaroConfigEntry
from .entity import FibaroEntity


async def async_setup_entry(
    menuai: menuai,
    entry: FibaroConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Fibaro switches."""
    controller = entry.runtime_data
    async_add_entities(
        [FibaroSwitch(device) for device in controller.fibaro_devices[Platform.SWITCH]],
        True,
    )


class FibaroSwitch(FibaroEntity, SwitchEntity):
    """Representation of a Fibaro Switch."""

    def __init__(self, fibaro_device: DeviceModel) -> None:
        """Initialize the Fibaro device."""
        super().__init__(fibaro_device)
        self.entity_id = ENTITY_ID_FORMAT.format(self.ha_id)

    def turn_on(self, **kwargs: Any) -> None:
        """Turn device on."""
        self.call_turn_on()
        self._attr_is_on = True

    def turn_off(self, **kwargs: Any) -> None:
        """Turn device off."""
        self.call_turn_off()
        self._attr_is_on = False

    def update(self) -> None:
        """Update device state."""
        super().update()
        self._attr_is_on = self.current_binary_state
