"""Support for TP-Link LTE notifications."""

from __future__ import annotations

import logging
from typing import Any

import attr
import tp_connected

from menuai.components.notify import ATTR_TARGET, BaseNotificationService
from menuai.const import CONF_RECIPIENT
from menuai.core import menuai
from menuai.helpers.typing import ConfigType, DiscoveryInfoType

from . import DATA_KEY, LTEData

_LOGGER = logging.getLogger(__name__)


async def async_get_service(
    menuai: menuai,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
) -> TplinkNotifyService | None:
    """Get the notification service."""
    if discovery_info is None:
        return None
    return TplinkNotifyService(menuai, discovery_info)


@attr.s
class TplinkNotifyService(BaseNotificationService):
    """Implementation of a notification service."""

    menuai: menuai = attr.ib()
    config: dict[str, Any] = attr.ib()

    async def async_send_message(self, message: str = "", **kwargs: Any) -> None:
        """Send a message to a user."""

        lte_data: LTEData = self.menuai.data[DATA_KEY]
        modem_data = lte_data.get_modem_data(self.config)
        if not modem_data:
            _LOGGER.error("No modem available")
            return

        phone = self.config[CONF_RECIPIENT]
        targets = kwargs.get(ATTR_TARGET, phone)
        if targets and message:
            for target in targets:
                try:
                    await modem_data.modem.sms(target, message)
                except tp_connected.Error:
                    _LOGGER.error("Unable to send to %s", target)
