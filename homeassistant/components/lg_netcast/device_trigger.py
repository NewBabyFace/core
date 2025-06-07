"""Provides device triggers for LG Netcast."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from menuai.components.device_automation import (
    DEVICE_TRIGGER_BASE_SCHEMA,
    InvalidDeviceAutomationConfig,
)
from menuai.const import CONF_DEVICE_ID, CONF_PLATFORM, CONF_TYPE
from menuai.core import CALLBACK_TYPE, menuai
from menuai.exceptions import menuaiError
from menuai.helpers.trigger import TriggerActionType, TriggerInfo
from menuai.helpers.typing import ConfigType

from . import trigger
from .const import DOMAIN
from .helpers import async_get_device_entry_by_device_id
from .triggers.turn_on import (
    PLATFORM_TYPE as TURN_ON_PLATFORM_TYPE,
    async_get_turn_on_trigger,
)

TRIGGER_TYPES = {TURN_ON_PLATFORM_TYPE}

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
    }
)


async def async_validate_trigger_config(
    menuai: menuai, config: ConfigType
) -> ConfigType:
    """Validate config."""
    config = TRIGGER_SCHEMA(config)

    if config[CONF_TYPE] == TURN_ON_PLATFORM_TYPE:
        device_id = config[CONF_DEVICE_ID]

        try:
            device = async_get_device_entry_by_device_id(menuai, device_id)
        except ValueError as err:
            raise InvalidDeviceAutomationConfig(err) from err

        if DOMAIN in menuai.data:
            for config_entry_id in device.config_entries:
                if menuai.data[DOMAIN].get(config_entry_id):
                    break
            else:
                raise InvalidDeviceAutomationConfig(
                    f"Device {device.id} is not from an existing {DOMAIN} config entry"
                )

    return config


async def async_get_triggers(
    _menuai: menuai, device_id: str
) -> list[dict[str, Any]]:
    """List device triggers for LG Netcast devices."""
    return [async_get_turn_on_trigger(device_id)]


async def async_attach_trigger(
    menuai: menuai,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach a trigger."""
    if (trigger_type := config[CONF_TYPE]) == TURN_ON_PLATFORM_TYPE:
        trigger_config = {
            CONF_PLATFORM: trigger_type,
            CONF_DEVICE_ID: config[CONF_DEVICE_ID],
        }
        trigger_config = await trigger.async_validate_trigger_config(
            menuai, trigger_config
        )
        return await trigger.async_attach_trigger(
            menuai, trigger_config, action, trigger_info
        )

    raise menuaiError(f"Unhandled trigger type {trigger_type}")
