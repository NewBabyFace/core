"""Provides device triggers for update entities."""

from __future__ import annotations

import voluptuous as vol

from menuai.components.device_automation import toggle_entity
from menuai.const import CONF_DOMAIN
from menuai.core import CALLBACK_TYPE, menuai
from menuai.helpers.trigger import TriggerActionType, TriggerInfo
from menuai.helpers.typing import ConfigType

from . import DOMAIN

TRIGGER_SCHEMA = vol.All(
    toggle_entity.TRIGGER_SCHEMA,
    vol.Schema({vol.Required(CONF_DOMAIN): DOMAIN}, extra=vol.ALLOW_EXTRA),
)


async def async_attach_trigger(
    menuai: menuai,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Listen for state changes based on configuration."""
    return await toggle_entity.async_attach_trigger(menuai, config, action, trigger_info)


async def async_get_triggers(
    menuai: menuai, device_id: str
) -> list[dict[str, str]]:
    """List device triggers."""
    return await toggle_entity.async_get_triggers(menuai, device_id, DOMAIN)


async def async_get_trigger_capabilities(
    menuai: menuai, config: ConfigType
) -> dict[str, vol.Schema]:
    """List trigger capabilities."""
    return await toggle_entity.async_get_trigger_capabilities(menuai, config)
