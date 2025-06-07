"""Component for interfacing RFK101 proximity card readers."""

from __future__ import annotations

import logging

from rfk101py.rfk101py import rfk101py
import voluptuous as vol

from menuai.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    EVENT_menuai_STOP,
)
from menuai.core import Event, menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

DOMAIN = "idteck_prox"

EVENT_IDTECK_PROX_KEYCARD = "idteck_prox_keycard"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            cv.ensure_list,
            [
                vol.Schema(
                    {
                        vol.Required(CONF_HOST): cv.string,
                        vol.Required(CONF_PORT): cv.port,
                        vol.Required(CONF_NAME): cv.string,
                    }
                )
            ],
        )
    },
    extra=vol.ALLOW_EXTRA,
)


def setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the IDTECK proximity card component."""
    conf = config[DOMAIN]
    for unit in conf:
        host = unit[CONF_HOST]
        port = unit[CONF_PORT]
        name = unit[CONF_NAME]

        try:
            reader = IdteckReader(menuai, host, port, name)
            reader.connect()
            menuai.bus.listen_once(EVENT_menuai_STOP, reader.stop)
        except OSError as error:
            _LOGGER.error("Error creating %s. %s", name, error)
            return False

    return True


class IdteckReader:
    """Representation of an IDTECK proximity card reader."""

    def __init__(self, menuai, host, port, name):
        """Initialize the reader."""
        self.menuai = menuai
        self._host = host
        self._port = port
        self._name = name
        self._connection = None

    def connect(self):
        """Connect to the reader."""

        self._connection = rfk101py(self._host, self._port, self._callback)

    def _callback(self, card):
        """Send a keycard event message into MenuAI whenever a card is read."""
        self.menuai.bus.fire(
            EVENT_IDTECK_PROX_KEYCARD, {"card": card, "name": self._name}
        )

    def stop(self, _: Event) -> None:
        """Close resources."""
        if self._connection:
            self._connection.close()
            self._connection = None
