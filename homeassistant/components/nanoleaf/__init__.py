"""The Nanoleaf integration."""

from __future__ import annotations

import asyncio
from contextlib import suppress
import logging

from aionanoleaf import EffectsEvent, Nanoleaf, StateEvent, TouchEvent

from menuai.const import (
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_TOKEN,
    CONF_TYPE,
    Platform,
)
from menuai.core import menuai
from menuai.helpers import device_registry as dr
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, NANOLEAF_EVENT, TOUCH_GESTURE_TRIGGER_MAP, TOUCH_MODELS
from .coordinator import NanoleafConfigEntry, NanoleafCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BUTTON, Platform.EVENT, Platform.LIGHT]


async def async_setup_entry(menuai: menuai, entry: NanoleafConfigEntry) -> bool:
    """Set up Nanoleaf from a config entry."""
    nanoleaf = Nanoleaf(
        async_get_clientsession(menuai), entry.data[CONF_HOST], entry.data[CONF_TOKEN]
    )

    coordinator = NanoleafCoordinator(menuai, entry, nanoleaf)

    await coordinator.async_config_entry_first_refresh()

    async def light_event_callback(event: StateEvent | EffectsEvent) -> None:
        """Receive state and effect event."""
        coordinator.async_set_updated_data(None)

    if supports_touch := nanoleaf.model in TOUCH_MODELS:
        device_registry = dr.async_get(menuai)
        device_entry = device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, nanoleaf.serial_no)},
        )

        async def touch_event_callback(event: TouchEvent) -> None:
            """Receive touch event."""
            gesture_type = TOUCH_GESTURE_TRIGGER_MAP.get(event.gesture_id)
            if gesture_type is None:
                _LOGGER.warning(
                    "Received unknown touch gesture ID %s", event.gesture_id
                )
                return
            _LOGGER.debug("Received touch gesture %s", gesture_type)
            menuai.bus.async_fire(
                NANOLEAF_EVENT,
                {CONF_DEVICE_ID: device_entry.id, CONF_TYPE: gesture_type},
            )
            async_dispatcher_send(
                menuai, f"nanoleaf_gesture_{nanoleaf.serial_no}", gesture_type
            )

    event_listener = asyncio.create_task(
        nanoleaf.listen_events(
            state_callback=light_event_callback,
            effects_callback=light_event_callback,
            touch_callback=touch_event_callback if supports_touch else None,
        )
    )

    async def _cancel_listener() -> None:
        event_listener.cancel()
        with suppress(asyncio.CancelledError):
            await event_listener

    entry.async_on_unload(_cancel_listener)

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: NanoleafConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
