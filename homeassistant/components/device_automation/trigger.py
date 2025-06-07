"""Offer device oriented automation."""

from __future__ import annotations

from typing import Any, Protocol

import voluptuous as vol

from menuai.const import CONF_DOMAIN
from menuai.core import CALLBACK_TYPE, menuai
from menuai.helpers.trigger import TriggerActionType, TriggerInfo
from menuai.helpers.typing import ConfigType

from . import (
    DEVICE_TRIGGER_BASE_SCHEMA,
    DeviceAutomationType,
    async_get_device_automation_platform,
)
from .helpers import async_validate_device_automation_config

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend({}, extra=vol.ALLOW_EXTRA)


class DeviceAutomationTriggerProtocol(Protocol):
    """Define the format of device_trigger modules.

    Each module must define either TRIGGER_SCHEMA or async_validate_trigger_config.
    """

    TRIGGER_SCHEMA: vol.Schema

    async def async_validate_trigger_config(
        self, menuai: menuai, config: ConfigType
    ) -> ConfigType:
        """Validate config."""

    async def async_attach_trigger(
        self,
        menuai: menuai,
        config: ConfigType,
        action: TriggerActionType,
        trigger_info: TriggerInfo,
    ) -> CALLBACK_TYPE:
        """Attach a trigger."""

    async def async_get_trigger_capabilities(
        self, menuai: menuai, config: ConfigType
    ) -> dict[str, vol.Schema]:
        """List trigger capabilities."""

    async def async_get_triggers(
        self, menuai: menuai, device_id: str
    ) -> list[dict[str, Any]]:
        """List triggers."""


async def async_validate_trigger_config(
    menuai: menuai, config: ConfigType
) -> ConfigType:
    """Validate config."""
    return await async_validate_device_automation_config(
        menuai, config, TRIGGER_SCHEMA, DeviceAutomationType.TRIGGER
    )


async def async_attach_trigger(
    menuai: menuai,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Listen for trigger."""
    platform = await async_get_device_automation_platform(
        menuai, config[CONF_DOMAIN], DeviceAutomationType.TRIGGER
    )
    return await platform.async_attach_trigger(menuai, config, action, trigger_info)
