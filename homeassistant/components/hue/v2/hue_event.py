"""Handle forward of events transmitted by Hue devices to menuai."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiohue.v2 import HueBridgeV2
from aiohue.v2.controllers.events import EventType
from aiohue.v2.models.button import Button
from aiohue.v2.models.relative_rotary import RelativeRotary

from menuai.const import CONF_DEVICE_ID, CONF_ID, CONF_TYPE, CONF_UNIQUE_ID
from menuai.core import callback
from menuai.helpers import device_registry as dr
from menuai.util import slugify

from ..const import ATTR_HUE_EVENT, CONF_SUBTYPE, DOMAIN

CONF_CONTROL_ID = "control_id"
CONF_DURATION = "duration"
CONF_STEPS = "steps"

if TYPE_CHECKING:
    from ..bridge import HueBridge

LOGGER = logging.getLogger(__name__)


async def async_setup_hue_events(bridge: HueBridge):
    """Manage listeners for stateless Hue sensors that emit events."""
    menuai = bridge.menuai
    api: HueBridgeV2 = bridge.api  # to satisfy typing
    conf_entry = bridge.config_entry
    dev_reg = dr.async_get(menuai)

    btn_controller = api.sensors.button
    rotary_controller = api.sensors.relative_rotary

    @callback
    def handle_button_event(evt_type: EventType, hue_resource: Button) -> None:
        """Handle event from Hue button resource controller."""
        LOGGER.debug("Received button event: %s", hue_resource)

        # guard for missing button object on the resource
        if hue_resource.button is None:
            return

        hue_device = btn_controller.get_device(hue_resource.id)
        device = dev_reg.async_get_device(identifiers={(DOMAIN, hue_device.id)})

        # Fire event
        data = {
            # send slugified entity name as id = backwards compatibility with previous version
            CONF_ID: slugify(f"{hue_device.metadata.name} Button"),
            CONF_DEVICE_ID: device.id,  # type: ignore[union-attr]
            CONF_UNIQUE_ID: hue_resource.id,
            CONF_TYPE: hue_resource.button.button_report.event.value,
            CONF_SUBTYPE: hue_resource.metadata.control_id,
        }
        menuai.bus.async_fire(ATTR_HUE_EVENT, data)

    # add listener for updates from `button` resource
    conf_entry.async_on_unload(
        btn_controller.subscribe(
            handle_button_event, event_filter=EventType.RESOURCE_UPDATED
        )
    )

    @callback
    def handle_rotary_event(evt_type: EventType, hue_resource: RelativeRotary) -> None:
        """Handle event from Hue relative_rotary resource controller."""
        LOGGER.debug("Received relative_rotary event: %s", hue_resource)

        hue_device = btn_controller.get_device(hue_resource.id)
        device = dev_reg.async_get_device(identifiers={(DOMAIN, hue_device.id)})

        # Fire event
        data = {
            CONF_DEVICE_ID: device.id,  # type: ignore[union-attr]
            CONF_UNIQUE_ID: hue_resource.id,
            CONF_TYPE: hue_resource.relative_rotary.rotary_report.action.value,
            CONF_SUBTYPE: hue_resource.relative_rotary.rotary_report.rotation.direction.value,
            CONF_DURATION: hue_resource.relative_rotary.rotary_report.rotation.duration,
            CONF_STEPS: hue_resource.relative_rotary.rotary_report.rotation.steps,
        }
        menuai.bus.async_fire(ATTR_HUE_EVENT, data)

    # add listener for updates from `relative_rotary` resource
    conf_entry.async_on_unload(
        rotary_controller.subscribe(
            handle_rotary_event, event_filter=EventType.RESOURCE_UPDATED
        )
    )
