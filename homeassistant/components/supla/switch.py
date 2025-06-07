"""Support for SUPLA switch."""

from __future__ import annotations

import logging
from pprint import pformat
from typing import Any

from menuai.components.switch import SwitchEntity
from menuai.core import menuai
from menuai.helpers.entity_platform import AddEntitiesCallback
from menuai.helpers.typing import ConfigType, DiscoveryInfoType

from . import DOMAIN, SUPLA_COORDINATORS, SUPLA_SERVERS
from .entity import SuplaEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    menuai: menuai,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the SUPLA switches."""
    if discovery_info is None:
        return

    _LOGGER.debug("Discovery: %s", pformat(discovery_info))

    entities = []
    for device in discovery_info.values():
        server_name = device["server_name"]

        entities.append(
            SuplaSwitchEntity(
                device,
                menuai.data[DOMAIN][SUPLA_SERVERS][server_name],
                menuai.data[DOMAIN][SUPLA_COORDINATORS][server_name],
            )
        )

    async_add_entities(entities)


class SuplaSwitchEntity(SuplaEntity, SwitchEntity):
    """Representation of a SUPLA Switch."""

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        await self.async_action("TURN_ON")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        await self.async_action("TURN_OFF")

    @property
    def is_on(self):
        """Return true if switch is on."""
        if state := self.channel_data.get("state"):
            return state["on"]
        return False
