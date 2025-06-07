"""Provides device triggers for KNX."""

from __future__ import annotations

from typing import Any, Final

import voluptuous as vol

from menuai.components.device_automation import (
    DEVICE_TRIGGER_BASE_SCHEMA,
    InvalidDeviceAutomationConfig,
)
from menuai.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from menuai.core import CALLBACK_TYPE, menuai
from menuai.helpers import selector
from menuai.helpers.trigger import TriggerActionType, TriggerInfo
from menuai.helpers.typing import ConfigType

from . import trigger
from .const import DOMAIN, KNX_MODULE_KEY
from .trigger import (
    CONF_KNX_DESTINATION,
    CONF_KNX_GROUP_VALUE_READ,
    CONF_KNX_GROUP_VALUE_RESPONSE,
    CONF_KNX_GROUP_VALUE_WRITE,
    CONF_KNX_INCOMING,
    CONF_KNX_OUTGOING,
    PLATFORM_TYPE_TRIGGER_TELEGRAM,
    TELEGRAM_TRIGGER_SCHEMA,
    TRIGGER_SCHEMA as TRIGGER_TRIGGER_SCHEMA,
)

TRIGGER_TELEGRAM: Final = "telegram"

TRIGGER_SCHEMA: Final = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): TRIGGER_TELEGRAM,
        **TELEGRAM_TRIGGER_SCHEMA,
    }
)


async def async_get_triggers(
    menuai: menuai, device_id: str
) -> list[dict[str, Any]]:
    """List device triggers for KNX devices."""
    triggers = []

    knx = menuai.data[KNX_MODULE_KEY]
    if knx.interface_device.device.id == device_id:
        # Add trigger for KNX telegrams to interface device
        triggers.append(
            {
                # Default fields when initializing the trigger
                CONF_PLATFORM: "device",
                CONF_DOMAIN: DOMAIN,
                CONF_DEVICE_ID: device_id,
                CONF_TYPE: TRIGGER_TELEGRAM,
            }
        )

    return triggers


async def async_get_trigger_capabilities(
    menuai: menuai, config: ConfigType
) -> dict[str, vol.Schema]:
    """List trigger capabilities."""
    project = menuai.data[KNX_MODULE_KEY].project
    options = [
        selector.SelectOptionDict(value=ga.address, label=f"{ga.address} - {ga.name}")
        for ga in project.group_addresses.values()
    ]
    return {
        "extra_fields": vol.Schema(
            {
                vol.Optional(CONF_KNX_DESTINATION): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        multiple=True,
                        custom_value=True,
                        options=options,
                    ),
                ),
                vol.Optional(
                    CONF_KNX_GROUP_VALUE_WRITE, default=True
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_KNX_GROUP_VALUE_RESPONSE, default=True
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_KNX_GROUP_VALUE_READ, default=True
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_KNX_INCOMING, default=True
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_KNX_OUTGOING, default=True
                ): selector.BooleanSelector(),
            }
        )
    }


async def async_attach_trigger(
    menuai: menuai,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach a trigger."""
    # Remove device trigger specific fields and add trigger platform identifier
    trigger_config = {
        key: config[key] for key in (config.keys() & TELEGRAM_TRIGGER_SCHEMA.keys())
    } | {CONF_PLATFORM: PLATFORM_TYPE_TRIGGER_TELEGRAM}

    try:
        trigger_config = TRIGGER_TRIGGER_SCHEMA(trigger_config)
    except vol.Invalid as err:
        raise InvalidDeviceAutomationConfig(f"{err}") from err

    return await trigger.async_attach_trigger(
        menuai, config=trigger_config, action=action, trigger_info=trigger_info
    )
