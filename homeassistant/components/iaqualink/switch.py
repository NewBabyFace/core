"""Support for Aqualink pool feature switches."""

from __future__ import annotations

from typing import Any

from iaqualink.device import AqualinkSwitch

from menuai.components.switch import SwitchEntity
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AqualinkConfigEntry, refresh_system
from .entity import AqualinkEntity
from .utils import await_or_reraise

PARALLEL_UPDATES = 0


async def async_setup_entry(
    menuai: menuai,
    config_entry: AqualinkConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up discovered switches."""
    async_add_entities(
        (menuaiAqualinkSwitch(dev) for dev in config_entry.runtime_data.switches),
        True,
    )


class menuaiAqualinkSwitch(AqualinkEntity[AqualinkSwitch], SwitchEntity):
    """Representation of a switch."""

    def __init__(self, dev: AqualinkSwitch) -> None:
        """Initialize AquaLink switch."""
        super().__init__(dev)
        name = self._attr_name = dev.label
        if name == "Cleaner":
            self._attr_icon = "mdi:robot-vacuum"
        elif name == "Waterfall" or name.endswith("Dscnt"):
            self._attr_icon = "mdi:fountain"
        elif name.endswith(("Pump", "Blower")):
            self._attr_icon = "mdi:fan"
        if name.endswith("Heater"):
            self._attr_icon = "mdi:radiator"

    @property
    def is_on(self) -> bool:
        """Return whether the switch is on or not."""
        return self.dev.is_on

    @refresh_system
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        await await_or_reraise(self.dev.turn_on())

    @refresh_system
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        await await_or_reraise(self.dev.turn_off())
