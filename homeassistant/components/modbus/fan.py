"""Support for Modbus fans."""

from __future__ import annotations

from typing import Any

from menuai.components.fan import FanEntity, FanEntityFeature
from menuai.const import CONF_NAME
from menuai.core import menuai
from menuai.helpers.entity_platform import AddEntitiesCallback
from menuai.helpers.typing import ConfigType, DiscoveryInfoType

from . import get_hub
from .const import CONF_FANS
from .entity import BaseSwitch
from .modbus import ModbusHub

PARALLEL_UPDATES = 1


async def async_setup_platform(
    menuai: menuai,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Read configuration and create Modbus fans."""
    if discovery_info is None or not (fans := discovery_info[CONF_FANS]):
        return
    hub = get_hub(menuai, discovery_info[CONF_NAME])
    async_add_entities(ModbusFan(menuai, hub, config) for config in fans)


class ModbusFan(BaseSwitch, FanEntity):
    """Class representing a Modbus fan."""

    def __init__(
        self, menuai: menuai, hub: ModbusHub, config: dict[str, Any]
    ) -> None:
        """Initialize the fan."""
        super().__init__(menuai, hub, config)
        if self.command_on is not None and self._command_off is not None:
            self._attr_supported_features |= (
                FanEntityFeature.TURN_OFF | FanEntityFeature.TURN_ON
            )

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Set fan on."""
        await self.async_turn(self.command_on)

    @property
    def is_on(self) -> bool | None:
        """Return true if fan is on.

        This is needed due to the ongoing conversion of fan.
        """
        return self._attr_is_on
