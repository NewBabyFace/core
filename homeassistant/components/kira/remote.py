"""Support for Keene Electronics IR-IP devices."""

from __future__ import annotations

from collections.abc import Iterable
import logging
from typing import Any

from menuai.components import remote
from menuai.const import CONF_DEVICE, CONF_NAME
from menuai.core import menuai
from menuai.helpers.entity_platform import AddEntitiesCallback
from menuai.helpers.typing import ConfigType, DiscoveryInfoType

from . import CONF_REMOTE, DOMAIN

_LOGGER = logging.getLogger(__name__)


def setup_platform(
    menuai: menuai,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Kira platform."""
    if discovery_info:
        name = discovery_info.get(CONF_NAME)
        device = discovery_info.get(CONF_DEVICE)

        kira = menuai.data[DOMAIN][CONF_REMOTE][name]
        add_entities([KiraRemote(device, kira)])


class KiraRemote(remote.RemoteEntity):
    """Remote representation used to send commands to a Kira device."""

    def __init__(self, name, kira):
        """Initialize KiraRemote class."""
        _LOGGER.debug("KiraRemote device init started for: %s", name)
        self._attr_name = name
        self._kira = kira

    def send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        """Send a command to one device."""
        for single_command in command:
            code_tuple = (single_command, kwargs.get(remote.ATTR_DEVICE))
            _LOGGER.debug("Sending Command: %s to %s", *code_tuple)
            self._kira.sendCode(code_tuple)
