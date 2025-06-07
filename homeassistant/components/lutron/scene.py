"""Support for Lutron scenes."""

from __future__ import annotations

from typing import Any

from pylutron import Button, Keypad, Lutron

from menuai.components.scene import Scene
from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DOMAIN, LutronData
from .entity import LutronKeypad


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Lutron scene platform.

    Adds scenes from the Main Repeater associated with the config_entry as
    scene entities.
    """
    entry_data: LutronData = menuai.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        LutronScene(area_name, keypad, device, entry_data.client)
        for area_name, keypad, device, led in entry_data.scenes
    )


class LutronScene(LutronKeypad, Scene):
    """Representation of a Lutron Scene."""

    _lutron_device: Button

    def __init__(
        self,
        area_name: str,
        keypad: Keypad,
        lutron_device: Button,
        controller: Lutron,
    ) -> None:
        """Initialize the scene/button."""
        super().__init__(area_name, lutron_device, controller, keypad)
        self._attr_name = lutron_device.name

    def activate(self, **kwargs: Any) -> None:
        """Activate the scene."""
        self._lutron_device.tap()
