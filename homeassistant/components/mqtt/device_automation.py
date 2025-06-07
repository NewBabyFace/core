"""Provides device automations for MQTT."""

from __future__ import annotations

import functools

import voluptuous as vol

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.typing import ConfigType, DiscoveryInfoType

from . import device_trigger
from .config import MQTT_BASE_SCHEMA
from .entity import async_setup_non_entity_entry_helper

AUTOMATION_TYPE_TRIGGER = "trigger"
AUTOMATION_TYPES = [AUTOMATION_TYPE_TRIGGER]
AUTOMATION_TYPES_SCHEMA = vol.In(AUTOMATION_TYPES)
CONF_AUTOMATION_TYPE = "automation_type"

DISCOVERY_SCHEMA = MQTT_BASE_SCHEMA.extend(
    {vol.Required(CONF_AUTOMATION_TYPE): AUTOMATION_TYPES_SCHEMA},
    extra=vol.ALLOW_EXTRA,
)


async def async_setup_entry(menuai: menuai, config_entry: ConfigEntry) -> None:
    """Set up MQTT device automation dynamically through MQTT discovery."""

    setup = functools.partial(_async_setup_automation, menuai, config_entry=config_entry)
    async_setup_non_entity_entry_helper(
        menuai, "device_automation", setup, DISCOVERY_SCHEMA
    )


async def _async_setup_automation(
    menuai: menuai,
    config: ConfigType,
    config_entry: ConfigEntry,
    discovery_data: DiscoveryInfoType,
) -> None:
    """Set up an MQTT device automation."""
    if config[CONF_AUTOMATION_TYPE] == AUTOMATION_TYPE_TRIGGER:
        await device_trigger.async_setup_trigger(
            menuai, config, config_entry, discovery_data
        )


async def async_removed_from_device(menuai: menuai, device_id: str) -> None:
    """Handle Mqtt removed from a device."""
    await device_trigger.async_removed_from_device(menuai, device_id)
