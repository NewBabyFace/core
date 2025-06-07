"""Provides a binary sensor which gets its values from a TCP socket."""

from __future__ import annotations

from typing import Final

from menuai.components.binary_sensor import (
    PLATFORM_SCHEMA as BINARY_SENSOR_PLATFORM_SCHEMA,
    BinarySensorEntity,
)
from menuai.core import menuai
from menuai.helpers.entity_platform import AddEntitiesCallback
from menuai.helpers.typing import ConfigType, DiscoveryInfoType

from .common import TCP_PLATFORM_SCHEMA
from .const import CONF_VALUE_ON
from .entity import TcpEntity

PLATFORM_SCHEMA: Final = BINARY_SENSOR_PLATFORM_SCHEMA.extend(TCP_PLATFORM_SCHEMA)


def setup_platform(
    menuai: menuai,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the TCP binary sensor."""
    add_entities([TcpBinarySensor(menuai, config)])


class TcpBinarySensor(TcpEntity, BinarySensorEntity):
    """A binary sensor which is on when its state == CONF_VALUE_ON."""

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self._state == self._config[CONF_VALUE_ON]
