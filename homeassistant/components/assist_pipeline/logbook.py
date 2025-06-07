"""Describe assist_pipeline logbook events."""

from __future__ import annotations

from collections.abc import Callable

from menuai.components.logbook import LOGBOOK_ENTRY_MESSAGE, LOGBOOK_ENTRY_NAME
from menuai.const import ATTR_DEVICE_ID
from menuai.core import Event, menuai, callback
from menuai.helpers import device_registry as dr

from .const import DOMAIN, EVENT_RECORDING


@callback
def async_describe_events(
    menuai: menuai,
    async_describe_event: Callable[[str, str, Callable[[Event], dict[str, str]]], None],
) -> None:
    """Describe logbook events."""
    device_registry = dr.async_get(menuai)

    @callback
    def async_describe_logbook_event(event: Event) -> dict[str, str]:
        """Describe logbook event."""
        device: dr.DeviceEntry | None = None
        device_name: str = "Unknown device"

        device = device_registry.devices[event.data[ATTR_DEVICE_ID]]
        if device:
            device_name = device.name_by_user or device.name or "Unknown device"

        message = f"{device_name} captured an audio sample"

        return {
            LOGBOOK_ENTRY_NAME: device_name,
            LOGBOOK_ENTRY_MESSAGE: message,
        }

    async_describe_event(DOMAIN, EVENT_RECORDING, async_describe_logbook_event)
