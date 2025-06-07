"""Helpers for device oriented automations."""

from __future__ import annotations

from typing import cast

import voluptuous as vol

from menuai.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.helpers.typing import ConfigType

from . import DeviceAutomationType, async_get_device_automation_platform
from .exceptions import InvalidDeviceAutomationConfig

DYNAMIC_VALIDATOR = {
    DeviceAutomationType.ACTION: "async_validate_action_config",
    DeviceAutomationType.CONDITION: "async_validate_condition_config",
    DeviceAutomationType.TRIGGER: "async_validate_trigger_config",
}

STATIC_VALIDATOR = {
    DeviceAutomationType.ACTION: "ACTION_SCHEMA",
    DeviceAutomationType.CONDITION: "CONDITION_SCHEMA",
    DeviceAutomationType.TRIGGER: "TRIGGER_SCHEMA",
}

ENTITY_PLATFORMS = {
    Platform.ALARM_CONTROL_PANEL.value,
    Platform.BUTTON.value,
    Platform.CLIMATE.value,
    Platform.COVER.value,
    Platform.FAN.value,
    Platform.HUMIDIFIER.value,
    Platform.LIGHT.value,
    Platform.LOCK.value,
    Platform.NUMBER.value,
    Platform.REMOTE.value,
    Platform.SELECT.value,
    Platform.SWITCH.value,
    Platform.TEXT.value,
    Platform.VACUUM.value,
    Platform.WATER_HEATER.value,
}


async def async_validate_device_automation_config(
    menuai: menuai,
    config: ConfigType,
    automation_schema: vol.Schema,
    automation_type: DeviceAutomationType,
) -> ConfigType:
    """Validate config."""
    validated_config: ConfigType = automation_schema(config)
    platform = await async_get_device_automation_platform(
        menuai, validated_config[CONF_DOMAIN], automation_type
    )

    # Make sure the referenced device and optional entity exist
    device_registry = dr.async_get(menuai)
    if not (device := device_registry.async_get(validated_config[CONF_DEVICE_ID])):
        # The device referenced by the device automation does not exist
        raise InvalidDeviceAutomationConfig(
            f"Unknown device '{validated_config[CONF_DEVICE_ID]}'"
        )
    if entity_id := validated_config.get(CONF_ENTITY_ID):
        try:
            er.async_validate_entity_id(er.async_get(menuai), entity_id)
        except vol.Invalid as err:
            raise InvalidDeviceAutomationConfig(
                f"Unknown entity '{entity_id}'"
            ) from err

    if not hasattr(platform, DYNAMIC_VALIDATOR[automation_type]):
        # Pass the unvalidated config to avoid mutating the raw config twice
        return cast(
            ConfigType, getattr(platform, STATIC_VALIDATOR[automation_type])(config)
        )

    # Devices are not linked to config entries from entity platform domains, skip
    # the checks below which look for a config entry matching the device automation
    # domain
    if (
        automation_type == DeviceAutomationType.ACTION
        and validated_config[CONF_DOMAIN] in ENTITY_PLATFORMS
    ):
        # Pass the unvalidated config to avoid mutating the raw config twice
        return cast(
            ConfigType,
            await getattr(platform, DYNAMIC_VALIDATOR[automation_type])(menuai, config),
        )

    # Find a config entry with the same domain as the device automation
    device_config_entry = None
    for entry_id in device.config_entries:
        if (
            not (entry := menuai.config_entries.async_get_entry(entry_id))
            or entry.domain != validated_config[CONF_DOMAIN]
        ):
            continue
        device_config_entry = entry
        break

    if not device_config_entry:
        # There's no config entry with the same domain as the device automation
        raise InvalidDeviceAutomationConfig(
            f"Device '{validated_config[CONF_DEVICE_ID]}' has no config entry from "
            f"domain '{validated_config[CONF_DOMAIN]}'"
        )

    if not await menuai.config_entries.async_wait_component(device_config_entry):
        # The component could not be loaded, skip the dynamic validation
        return validated_config

    # Pass the unvalidated config to avoid mutating the raw config twice
    return cast(
        ConfigType,
        await getattr(platform, DYNAMIC_VALIDATOR[automation_type])(menuai, config),
    )
