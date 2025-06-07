"""DROP device data update coordinator object."""

from __future__ import annotations

import logging

from dropmqttapi.mqttapi import DropAPI

from menuai.components import mqtt
from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_COMMAND_TOPIC, DOMAIN

_LOGGER = logging.getLogger(__name__)


type DROPConfigEntry = ConfigEntry[DROPDeviceDataUpdateCoordinator]


class DROPDeviceDataUpdateCoordinator(DataUpdateCoordinator[None]):
    """DROP device object."""

    config_entry: DROPConfigEntry

    def __init__(self, menuai: menuai, entry: DROPConfigEntry) -> None:
        """Initialize the device."""
        super().__init__(
            menuai, _LOGGER, config_entry=entry, name=f"{DOMAIN}-{entry.unique_id}"
        )
        self.drop_api = DropAPI()

    async def set_water(self, value: int) -> None:
        """Change water supply state."""
        payload = self.drop_api.set_water_message(value)
        await mqtt.async_publish(
            self.menuai,
            self.config_entry.data[CONF_COMMAND_TOPIC],
            payload,
        )

    async def set_bypass(self, value: int) -> None:
        """Change water bypass state."""
        payload = self.drop_api.set_bypass_message(value)
        await mqtt.async_publish(
            self.menuai,
            self.config_entry.data[CONF_COMMAND_TOPIC],
            payload,
        )

    async def set_protect_mode(self, value: str) -> None:
        """Change protect mode state."""
        payload = self.drop_api.set_protect_mode_message(value)
        await mqtt.async_publish(
            self.menuai,
            self.config_entry.data[CONF_COMMAND_TOPIC],
            payload,
        )
