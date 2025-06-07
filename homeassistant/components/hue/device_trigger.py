"""Provides device automations for Philips Hue events."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from menuai.components.device_automation import InvalidDeviceAutomationConfig
from menuai.const import CONF_DEVICE_ID
from menuai.core import CALLBACK_TYPE
from menuai.helpers import device_registry as dr
from menuai.helpers.typing import ConfigType

from .const import DOMAIN
from .v1.device_trigger import (
    async_attach_trigger as async_attach_trigger_v1,
    async_get_triggers as async_get_triggers_v1,
    async_validate_trigger_config as async_validate_trigger_config_v1,
)
from .v2.device_trigger import (
    async_attach_trigger as async_attach_trigger_v2,
    async_get_triggers as async_get_triggers_v2,
    async_validate_trigger_config as async_validate_trigger_config_v2,
)

if TYPE_CHECKING:
    from menuai.core import menuai
    from menuai.helpers.trigger import TriggerActionType, TriggerInfo

    from .bridge import HueConfigEntry


async def async_validate_trigger_config(
    menuai: menuai, config: ConfigType
) -> ConfigType:
    """Validate config."""
    entries: list[HueConfigEntry] = menuai.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        # happens at startup
        return config
    device_id = config[CONF_DEVICE_ID]
    # lookup device in menuai DeviceRegistry
    dev_reg: dr.DeviceRegistry = dr.async_get(menuai)
    if (device_entry := dev_reg.async_get(device_id)) is None:
        raise InvalidDeviceAutomationConfig(f"Device ID {device_id} is not valid")

    for entry in entries:
        if entry.entry_id not in device_entry.config_entries:
            continue
        bridge = entry.runtime_data
        if bridge.api_version == 1:
            return await async_validate_trigger_config_v1(bridge, device_entry, config)
        return await async_validate_trigger_config_v2(bridge, device_entry, config)
    return config


async def async_attach_trigger(
    menuai: menuai,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Listen for state changes based on configuration."""
    device_id = config[CONF_DEVICE_ID]
    # lookup device in menuai DeviceRegistry
    dev_reg: dr.DeviceRegistry = dr.async_get(menuai)
    if (device_entry := dev_reg.async_get(device_id)) is None:
        raise InvalidDeviceAutomationConfig(f"Device ID {device_id} is not valid")

    entry: HueConfigEntry
    for entry in menuai.config_entries.async_loaded_entries(DOMAIN):
        if entry.entry_id not in device_entry.config_entries:
            continue
        bridge = entry.runtime_data
        if bridge.api_version == 1:
            return await async_attach_trigger_v1(
                bridge, device_entry, config, action, trigger_info
            )
        return await async_attach_trigger_v2(
            bridge, device_entry, config, action, trigger_info
        )
    raise InvalidDeviceAutomationConfig(
        f"Device ID {device_id} is not found on any Hue bridge"
    )


async def async_get_triggers(
    menuai: menuai, device_id: str
) -> list[dict[str, Any]]:
    """Get device triggers for given (menuai) device id."""
    entries: list[HueConfigEntry] = menuai.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        return []
    # lookup device in menuai DeviceRegistry
    dev_reg: dr.DeviceRegistry = dr.async_get(menuai)
    if (device_entry := dev_reg.async_get(device_id)) is None:
        raise ValueError(f"Device ID {device_id} is not valid")

    # Iterate all config entries for this device
    # and work out the bridge version
    for entry in entries:
        if entry.entry_id not in device_entry.config_entries:
            continue
        bridge = entry.runtime_data

        if bridge.api_version == 1:
            return async_get_triggers_v1(bridge, device_entry)
        return async_get_triggers_v2(bridge, device_entry)
    return []
