"""Identify support for WMS WebControl pro."""

from __future__ import annotations

from wmspro.const import WMS_WebControl_pro_API_actionDescription

from menuai.components.button import ButtonDeviceClass, ButtonEntity
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import WebControlProConfigEntry
from .entity import WebControlProGenericEntity


async def async_setup_entry(
    menuai: menuai,
    config_entry: WebControlProConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the WMS based identify buttons from a config entry."""
    hub = config_entry.runtime_data

    entities: list[WebControlProGenericEntity] = [
        WebControlProIdentifyButton(config_entry.entry_id, dest)
        for dest in hub.dests.values()
        if dest.action(WMS_WebControl_pro_API_actionDescription.Identify)
    ]

    async_add_entities(entities)


class WebControlProIdentifyButton(WebControlProGenericEntity, ButtonEntity):
    """Representation of a WMS based identify button."""

    _attr_device_class = ButtonDeviceClass.IDENTIFY

    async def async_press(self) -> None:
        """Handle the button press."""
        action = self._dest.action(WMS_WebControl_pro_API_actionDescription.Identify)
        await action()
