"""Demo platform that offers a fake button entity."""

from __future__ import annotations

from menuai.components import persistent_notification
from menuai.components.button import ButtonEntity
from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.device_registry import DeviceInfo
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DOMAIN


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the demo button platform."""
    async_add_entities(
        [
            DemoButton(
                unique_id="push",
                device_name="Push",
            ),
        ]
    )


class DemoButton(ButtonEntity):
    """Representation of a demo button entity."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_should_poll = False

    def __init__(
        self,
        unique_id: str,
        device_name: str,
    ) -> None:
        """Initialize the Demo button entity."""
        self._attr_unique_id = unique_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            name=device_name,
        )

    async def async_press(self) -> None:
        """Send out a persistent notification."""
        persistent_notification.async_create(
            self.menuai, "Button pressed", title="Button"
        )
        self.menuai.bus.async_fire("demo_button_pressed")
