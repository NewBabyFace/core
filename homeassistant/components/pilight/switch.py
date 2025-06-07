"""Support for switching devices via Pilight to on and off."""

from __future__ import annotations

import voluptuous as vol

from menuai.components.switch import (
    PLATFORM_SCHEMA as SWITCH_PLATFORM_SCHEMA,
    SwitchEntity,
)
from menuai.const import CONF_SWITCHES
from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.entity_platform import AddEntitiesCallback
from menuai.helpers.typing import ConfigType, DiscoveryInfoType

from .entity import SWITCHES_SCHEMA, PilightBaseDevice

PLATFORM_SCHEMA = SWITCH_PLATFORM_SCHEMA.extend(
    {vol.Required(CONF_SWITCHES): vol.Schema({cv.string: SWITCHES_SCHEMA})}
)


def setup_platform(
    menuai: menuai,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Pilight platform."""
    switches = config[CONF_SWITCHES]
    devices = []

    for dev_name, dev_config in switches.items():
        devices.append(PilightSwitch(menuai, dev_name, dev_config))

    add_entities(devices)


class PilightSwitch(PilightBaseDevice, SwitchEntity):
    """Representation of a Pilight switch."""
