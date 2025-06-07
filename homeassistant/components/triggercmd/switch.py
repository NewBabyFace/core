"""Platform for switch integration."""

from __future__ import annotations

import logging
from typing import Any

from triggercmd import client, ha

from menuai.components.switch import SwitchEntity
from menuai.core import menuai
from menuai.helpers.device_registry import DeviceInfo
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TriggercmdConfigEntry
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    menuai: menuai,
    config_entry: TriggercmdConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add switch for passed config_entry in HA."""
    hub = config_entry.runtime_data
    async_add_entities(TRIGGERcmdSwitch(trigger) for trigger in hub.triggers)


class TRIGGERcmdSwitch(SwitchEntity):
    """Representation of a Switch."""

    _attr_has_entity_name = True
    _attr_assumed_state = True
    _attr_should_poll = False

    computer_id: str
    trigger_id: str
    firmware_version: str
    model: str
    hub: ha.Hub

    def __init__(self, trigger: TRIGGERcmdSwitch) -> None:
        """Initialize the switch."""
        self._switch = trigger
        self._attr_is_on = False
        self._attr_unique_id = f"{trigger.computer_id}.{trigger.trigger_id}"
        self._attr_name = trigger.trigger_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, trigger.computer_id)},
            name=trigger.computer_id.capitalize(),
            sw_version=trigger.firmware_version,
            model=trigger.model,
            manufacturer=trigger.hub.manufacturer,
        )

    @property
    def available(self) -> bool:
        """Return True if hub is available."""
        return self._switch.hub.online

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.trigger("on")
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.trigger("off")
        self._attr_is_on = False
        self.async_write_ha_state()

    async def trigger(self, params: str):
        """Trigger the command."""
        r = await client.async_trigger(
            self._switch.hub.token,
            {
                "computer": self._switch.computer_id,
                "trigger": self._switch.trigger_id,
                "params": params,
                "sender": "MenuAI",
            },
        )
        _LOGGER.debug("TRIGGERcmd trigger response: %s", r.json())
