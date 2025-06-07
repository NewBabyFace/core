"""Support for Pilight sensors."""

from __future__ import annotations

import logging

import voluptuous as vol

from menuai.components.sensor import (
    PLATFORM_SCHEMA as SENSOR_PLATFORM_SCHEMA,
    SensorEntity,
)
from menuai.const import CONF_NAME, CONF_PAYLOAD, CONF_UNIT_OF_MEASUREMENT
from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.entity_platform import AddEntitiesCallback
from menuai.helpers.typing import ConfigType, DiscoveryInfoType

from . import EVENT

_LOGGER = logging.getLogger(__name__)

CONF_VARIABLE = "variable"

DEFAULT_NAME = "Pilight Sensor"
PLATFORM_SCHEMA = SENSOR_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_VARIABLE): cv.string,
        vol.Required(CONF_PAYLOAD): vol.Schema(dict),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_UNIT_OF_MEASUREMENT): cv.string,
    }
)


def setup_platform(
    menuai: menuai,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up Pilight Sensor."""
    add_entities(
        [
            PilightSensor(
                menuai=menuai,
                name=config.get(CONF_NAME),
                variable=config.get(CONF_VARIABLE),
                payload=config.get(CONF_PAYLOAD),
                unit_of_measurement=config.get(CONF_UNIT_OF_MEASUREMENT),
            )
        ]
    )


class PilightSensor(SensorEntity):
    """Representation of a sensor that can be updated using Pilight."""

    _attr_should_poll = False

    def __init__(self, menuai, name, variable, payload, unit_of_measurement):
        """Initialize the sensor."""
        self._state = None
        self._menuai = menuai
        self._name = name
        self._variable = variable
        self._payload = payload
        self._unit_of_measurement = unit_of_measurement

        menuai.bus.listen(EVENT, self._handle_code)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def native_unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        return self._unit_of_measurement

    @property
    def native_value(self):
        """Return the state of the entity."""
        return self._state

    def _handle_code(self, call):
        """Handle received code by the pilight-daemon.

        If the code matches the defined payload
        of this sensor the sensor state is changed accordingly.
        """
        # Check if received code matches defined payload
        # True if payload is contained in received code dict, not
        # all items have to match
        if self._payload.items() <= call.data.items():
            try:
                value = call.data[self._variable]
                self._state = value
                self.schedule_update_ha_state()
            except KeyError:
                _LOGGER.error(
                    "No variable %s in received code data %s",
                    str(self._variable),
                    str(call.data),
                )
