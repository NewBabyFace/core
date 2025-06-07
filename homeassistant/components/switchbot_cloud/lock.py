"""Support for the Switchbot lock."""

from typing import Any

from switchbot_api import LockCommands

from menuai.components.lock import LockEntity
from menuai.config_entries import ConfigEntry
from menuai.core import menuai
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
        SwitchBotCloudLock(data.api, device, coordinator)
        for device, coordinator in data.devices.locks
    )


class SwitchBotCloudLock(SwitchBotCloudEntity, LockEntity):
    """Representation of a SwitchBot lock."""

    _attr_name = None

    def _set_attributes(self) -> None:
        """Set attributes from coordinator data."""
        if coord_data := self.coordinator.data:
            self._attr_is_locked = coord_data["lockState"] == "locked"

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the lock."""
        await self.send_api_command(LockCommands.LOCK)
        self._attr_is_locked = True
        self.async_write_ha_state()

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the lock."""

        await self.send_api_command(LockCommands.UNLOCK)
        self._attr_is_locked = False
        self.async_write_ha_state()
