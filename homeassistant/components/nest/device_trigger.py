"""Provides device automations for Nest."""

from __future__ import annotations

import voluptuous as vol

from menuai.components.device_automation import (
    DEVICE_TRIGGER_BASE_SCHEMA,
    InvalidDeviceAutomationConfig,
)
from menuai.components.menuai.triggers import event as event_trigger
from menuai.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from menuai.core import CALLBACK_TYPE, menuai
from menuai.helpers.trigger import TriggerActionType, TriggerInfo
from menuai.helpers.typing import ConfigType

from .const import DOMAIN
from .device_info import async_nest_devices_by_device_id
from .events import DEVICE_TRAIT_TRIGGER_MAP, NEST_EVENT

DEVICE = "device"

TRIGGER_TYPES = set(DEVICE_TRAIT_TRIGGER_MAP.values())

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
    }
)


async def async_get_triggers(
    menuai: menuai, device_id: str
) -> list[dict[str, str]]:
    """List device triggers for a Nest device."""
    devices = async_nest_devices_by_device_id(menuai)
    if not (device := devices.get(device_id)):
        raise InvalidDeviceAutomationConfig(f"Device not found {device_id}")
    trigger_types = [
        trigger_type
        for trait in device.traits
        if (trigger_type := DEVICE_TRAIT_TRIGGER_MAP.get(trait))
    ]
    return [
        {
            CONF_PLATFORM: DEVICE,
            CONF_DEVICE_ID: device_id,
            CONF_DOMAIN: DOMAIN,
            CONF_TYPE: trigger_type,
        }
        for trigger_type in trigger_types
    ]


async def async_attach_trigger(
    menuai: menuai,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach a trigger."""
    event_config = event_trigger.TRIGGER_SCHEMA(
        {
            event_trigger.CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: NEST_EVENT,
            event_trigger.CONF_EVENT_DATA: {
                CONF_DEVICE_ID: config[CONF_DEVICE_ID],
                CONF_TYPE: config[CONF_TYPE],
            },
        }
    )
    return await event_trigger.async_attach_trigger(
        menuai, event_config, action, trigger_info, platform_type="device"
    )
