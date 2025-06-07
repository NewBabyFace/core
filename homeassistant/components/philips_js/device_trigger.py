"""Provides device automations for control of device."""

from __future__ import annotations

import voluptuous as vol

from menuai.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from menuai.const import CONF_DEVICE_ID, CONF_TYPE
from menuai.core import CALLBACK_TYPE, menuai
from menuai.exceptions import menuaiError
from menuai.helpers.trigger import (
    PluggableAction,
    TriggerActionType,
    TriggerInfo,
)
from menuai.helpers.typing import ConfigType

from .const import DOMAIN, TRIGGER_TYPE_TURN_ON
from .helpers import async_get_turn_on_trigger

TRIGGER_TYPES = {TRIGGER_TYPE_TURN_ON}
TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
    }
)


async def async_get_triggers(
    menuai: menuai, device_id: str
) -> list[dict[str, str]]:
    """List device triggers for device."""
    triggers = []
    triggers.append(async_get_turn_on_trigger(device_id))

    return triggers


async def async_attach_trigger(
    menuai: menuai,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach a trigger."""
    trigger_data = trigger_info["trigger_data"]
    if (trigger_type := config[CONF_TYPE]) == TRIGGER_TYPE_TURN_ON:
        variables = {
            "trigger": {
                **trigger_data,
                "platform": "device",
                "domain": DOMAIN,
                "device_id": config[CONF_DEVICE_ID],
                "description": f"philips_js '{trigger_type}' event",
            }
        }

        turn_on_trigger = async_get_turn_on_trigger(config[CONF_DEVICE_ID])
        return PluggableAction.async_attach_trigger(
            menuai, turn_on_trigger, action, variables
        )

    raise menuaiError(f"Unhandled trigger type {trigger_type}")
