"""Demo platform that offers a fake event entity."""

from __future__ import annotations

from menuai.components.event import EventDeviceClass, EventEntity
from menuai.config_entries import ConfigEntry
from menuai.core import Event, menuai, callback
from menuai.helpers.device_registry import DeviceInfo
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DOMAIN


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the demo event platform."""
    async_add_entities([DemoEvent()])


class DemoEvent(EventEntity):
    """Representation of a demo event entity."""

    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = ["pressed"]
    _attr_has_entity_name = True
    _attr_name = "Button press"
    _attr_should_poll = False
    _attr_translation_key = "push"
    _attr_unique_id = "push"

    def __init__(self) -> None:
        """Initialize the Demo event entity."""
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "push")},
        )

    async def async_added_to_menuai(self) -> None:
        """Register callbacks."""
        self.menuai.bus.async_listen("demo_button_pressed", self._async_handle_event)

    @callback
    def _async_handle_event(self, _: Event) -> None:
        """Handle the demo button event."""
        self._trigger_event("pressed")
        self.async_write_ha_state()
