"""Support for the Switchbot Bot as a Button."""

from typing import Any

from switchbot_api import BotCommands

from menuai.components.button import ButtonEntity
from menuai.config_entries import ConfigEntry
from menuai.core import menuai, callback
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SwitchbotCloudData
from .const import DOMAIN
from .entity import SwitchBotCloudEntity


async def async_setup_entry(
    menuai: menuai,
    config: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up SwitchBot Cloud entry."""
    data: SwitchbotCloudData = menuai.data[DOMAIN][config.entry_id]
    async_add_entities(
        SwitchBotCloudBot(data.api, device, coordinator)
        for device, coordinator in data.devices.buttons
    )


class SwitchBotCloudBot(SwitchBotCloudEntity, ButtonEntity):
    """Representation of a SwitchBot Bot."""

    _attr_name = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

    async def async_press(self, **kwargs: Any) -> None:
        """Bot press command."""
        await self.send_api_command(BotCommands.PRESS)
