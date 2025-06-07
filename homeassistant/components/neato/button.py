"""Support for Neato buttons."""

from __future__ import annotations

from pybotvac import Robot

from menuai.components.button import ButtonEntity
from menuai.config_entries import ConfigEntry
from menuai.const import EntityCategory
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import NEATO_ROBOTS
from .entity import NeatoEntity


async def async_setup_entry(
    menuai: menuai,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Neato button from config entry."""
    entities = [NeatoDismissAlertButton(robot) for robot in menuai.data[NEATO_ROBOTS]]

    async_add_entities(entities, True)


class NeatoDismissAlertButton(NeatoEntity, ButtonEntity):
    """Representation of a dismiss_alert button entity."""

    _attr_translation_key = "dismiss_alert"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        robot: Robot,
    ) -> None:
        """Initialize a dismiss_alert Neato button entity."""
        super().__init__(robot)
        self._attr_unique_id = f"{robot.serial}_dismiss_alert"

    async def async_press(self) -> None:
        """Press the button."""
        await self.menuai.async_add_executor_job(self.robot.dismiss_current_alert)
