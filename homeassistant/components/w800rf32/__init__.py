"""Support for w800rf32 devices."""

import logging

import voluptuous as vol
import W800rf32 as w800

from menuai.const import (
    CONF_DEVICE,
    EVENT_menuai_START,
    EVENT_menuai_STOP,
)
from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.dispatcher import dispatcher_send
from menuai.helpers.typing import ConfigType

DATA_W800RF32 = "data_w800rf32"
DOMAIN = "w800rf32"

W800RF32_DEVICE = "w800rf32_{}"

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({vol.Required(CONF_DEVICE): cv.string})}, extra=vol.ALLOW_EXTRA
)


def setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the w800rf32 component."""

    # Declare the Handle event
    def handle_receive(event):
        """Handle received messages from w800rf32 gateway."""
        # Log event
        if not event.device:
            return
        _LOGGER.debug("Receive W800rf32 event in handle_receive")

        # Get device_type from device_id in menuai.data
        device_id = event.device.lower()
        signal = W800RF32_DEVICE.format(device_id)
        dispatcher_send(menuai, signal, event)

    # device --> /dev/ttyUSB0
    device = config[DOMAIN][CONF_DEVICE]
    w800_object = w800.Connect(device, None)

    def _start_w800rf32(event):
        w800_object.event_callback = handle_receive

    menuai.bus.listen_once(EVENT_menuai_START, _start_w800rf32)

    def _shutdown_w800rf32(event):
        """Close connection with w800rf32."""
        w800_object.close_connection()

    menuai.bus.listen_once(EVENT_menuai_STOP, _shutdown_w800rf32)

    menuai.data[DATA_W800RF32] = w800_object

    return True
