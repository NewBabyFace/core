"""Support for Modbus switches."""

from __future__ import annotations

from typing import Any

from menuai.components.switch import SwitchEntity
from menuai.const import CONF_NAME, CONF_SWITCHES
from menuai.core import menuai
from menuai.helpers.entity_platform import AddEntitiesCallback
from menuai.helpers.typing import ConfigType, DiscoveryInfoType

from . import get_hub
from .entity import BaseSwitch

PARALLEL_UPDATES = 1


async def async_setup_platform(
    menuai: menuai,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Read configuration and create Modbus switches."""
    if discovery_info is None or not (switches := discovery_info[CONF_SWITCHES]):
        return
    hub = get_hub(menuai, discovery_info[CONF_NAME])
    async_add_entities(ModbusSwitch(menuai, hub, config) for config in switches)


class ModbusSwitch(BaseSwitch, SwitchEntity):
    """Base class representing a Modbus switch."""

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Set switch on."""
        await self.async_turn(self.command_on)
