"""Triggers for WeMo devices."""

from __future__ import annotations

from pywemo.subscribe import EVENT_TYPE_LONG_PRESS
import voluptuous as vol

from menuai.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from menuai.components.menuai.triggers import event as event_trigger
from menuai.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from menuai.core import CALLBACK_TYPE, menuai
from menuai.helpers.trigger import TriggerActionType, TriggerInfo
from menuai.helpers.typing import ConfigType

from .const import DOMAIN, WEMO_SUBSCRIPTION_EVENT
from .coordinator import async_get_coordinator

TRIGGER_TYPES = {EVENT_TYPE_LONG_PRESS}

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
    }
)


async def async_get_triggers(
    menuai: menuai, device_id: str
) -> list[dict[str, str]]:
    """Return a list of triggers."""

    wemo_trigger = {
        # Required fields of TRIGGER_BASE_SCHEMA
        CONF_PLATFORM: "device",
        CONF_DOMAIN: DOMAIN,
        CONF_DEVICE_ID: device_id,
    }

    coordinator = async_get_coordinator(menuai, device_id)
    triggers = []

    # Check for long press support.
    if coordinator.supports_long_press:
        triggers.append(
            {
                # Required fields of TRIGGER_SCHEMA
                CONF_TYPE: EVENT_TYPE_LONG_PRESS,
                **wemo_trigger,
            }
        )

    return triggers


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
            event_trigger.CONF_EVENT_TYPE: WEMO_SUBSCRIPTION_EVENT,
            event_trigger.CONF_EVENT_DATA: {
                CONF_DEVICE_ID: config[CONF_DEVICE_ID],
                CONF_TYPE: config[CONF_TYPE],
            },
        }
    )
    return await event_trigger.async_attach_trigger(
        menuai, event_config, action, trigger_info, platform_type="device"
    )
