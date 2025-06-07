"""Provides device actions for Network UPS Tools (NUT)."""

from __future__ import annotations

from typing import cast

import voluptuous as vol

from menuai.components.device_automation import InvalidDeviceAutomationConfig
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_TYPE
from menuai.core import Context, menuai
from menuai.helpers import config_validation as cv, device_registry as dr
from menuai.helpers.typing import ConfigType, TemplateVarsType

from . import NutConfigEntry, NutRuntimeData
from .const import DOMAIN, INTEGRATION_SUPPORTED_COMMANDS

ACTION_TYPES = {cmd.replace(".", "_") for cmd in INTEGRATION_SUPPORTED_COMMANDS}

ACTION_SCHEMA = cv.DEVICE_ACTION_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(ACTION_TYPES),
    }
)


async def async_get_actions(
    menuai: menuai, device_id: str
) -> list[dict[str, str]]:
    """List device actions for Network UPS Tools (NUT) devices."""
    if (runtime_data := _get_runtime_data_from_device_id(menuai, device_id)) is None:
        return []
    base_action = {
        CONF_DEVICE_ID: device_id,
        CONF_DOMAIN: DOMAIN,
    }
    return [
        {CONF_TYPE: _get_device_action_name(command_name)} | base_action
        for command_name in runtime_data.user_available_commands
    ]


async def async_call_action_from_config(
    menuai: menuai,
    config: ConfigType,
    variables: TemplateVarsType,
    context: Context | None,
) -> None:
    """Execute a device action."""
    device_action_name: str = config[CONF_TYPE]
    command_name = _get_command_name(device_action_name)
    device_id: str = config[CONF_DEVICE_ID]

    if runtime_data := _get_runtime_data_from_device_id_exception_on_failure(
        menuai, device_id
    ):
        await runtime_data.data.async_run_command(command_name)


def _get_device_action_name(command_name: str) -> str:
    return command_name.replace(".", "_")


def _get_command_name(device_action_name: str) -> str:
    return device_action_name.replace("_", ".")


def _get_runtime_data_from_device_id(
    menuai: menuai,
    device_id: str,
) -> NutRuntimeData | None:
    """Find the runtime data for device ID and return None on error."""
    device_registry = dr.async_get(menuai)
    if (device := device_registry.async_get(device_id)) is None:
        return None
    return _get_runtime_data_for_device(menuai, device)


def _get_runtime_data_for_device(
    menuai: menuai, device: dr.DeviceEntry
) -> NutRuntimeData | None:
    """Find the runtime data for device and return None on error."""
    for config_entry_id in device.config_entries:
        entry = menuai.config_entries.async_get_entry(config_entry_id)
        if (
            entry
            and entry.domain == DOMAIN
            and entry.state is ConfigEntryState.LOADED
            and hasattr(entry, "runtime_data")
        ):
            return cast(NutConfigEntry, entry).runtime_data

    return None


def _get_runtime_data_from_device_id_exception_on_failure(
    menuai: menuai,
    device_id: str,
) -> NutRuntimeData | None:
    """Find the runtime data for device ID and raise exception on error."""
    device_registry = dr.async_get(menuai)
    if (device := device_registry.async_get(device_id)) is None:
        raise InvalidDeviceAutomationConfig(
            translation_domain=DOMAIN,
            translation_key="device_not_found",
            translation_placeholders={
                "device_id": device_id,
            },
        )

    if runtime_data := _get_runtime_data_for_device(menuai, device):
        return runtime_data

    raise InvalidDeviceAutomationConfig(
        translation_domain=DOMAIN,
        translation_key="config_invalid",
        translation_placeholders={
            "device_id": device_id,
        },
    )
