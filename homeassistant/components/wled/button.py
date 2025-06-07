"""Support for WLED button."""

from __future__ import annotations

from menuai.components.button import ButtonDeviceClass, ButtonEntity
from menuai.const import EntityCategory
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import WLEDConfigEntry
from .coordinator import WLEDDataUpdateCoordinator
from .entity import WLEDEntity
from .helpers import wled_exception_handler


async def async_setup_entry(
    menuai: menuai,
    entry: WLEDConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up WLED button based on a config entry."""
    async_add_entities([WLEDRestartButton(entry.runtime_data)])


class WLEDRestartButton(WLEDEntity, ButtonEntity):
    """Defines a WLED restart button."""

    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: WLEDDataUpdateCoordinator) -> None:
        """Initialize the button entity."""
        super().__init__(coordinator=coordinator)
        self._attr_unique_id = f"{coordinator.data.info.mac_address}_restart"

    @wled_exception_handler
    async def async_press(self) -> None:
        """Send out a restart command."""
        await self.coordinator.wled.reset()
