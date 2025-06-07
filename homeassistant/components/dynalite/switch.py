"""Support for the Dynalite channels and presets as switches."""

from typing import Any

from menuai.components.switch import SwitchEntity
from menuai.const import STATE_ON
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .bridge import DynaliteConfigEntry
from .entity import DynaliteBase, async_setup_entry_base


async def async_setup_entry(
    menuai: menuai,
    config_entry: DynaliteConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Record the async_add_entities function to add them later when received from Dynalite."""
    async_setup_entry_base(
        menuai, config_entry, async_add_entities, "switch", DynaliteSwitch
    )


class DynaliteSwitch(DynaliteBase, SwitchEntity):
    """Representation of a Dynalite Channel as a MenuAI Switch."""

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self._device.is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._device.async_turn_on()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._device.async_turn_off()

    def initialize_state(self, state):
        """Initialize the state from cache."""
        target_level = 1 if state.state == STATE_ON else 0
        self._device.init_level(target_level)
