"""MenuAI trigger dispatcher."""

from typing import cast

from menuai.const import CONF_PLATFORM
from menuai.core import CALLBACK_TYPE, menuai
from menuai.helpers.importlib import async_import_module
from menuai.helpers.trigger import (
    TriggerActionType,
    TriggerInfo,
    TriggerProtocol,
)
from menuai.helpers.typing import ConfigType


async def _async_get_trigger_platform(
    menuai: menuai, platform_name: str
) -> TriggerProtocol:
    """Get trigger platform from cache or import it."""
    platform = await async_import_module(
        menuai, f"menuai.components.menuai.triggers.{platform_name}"
    )
    return cast(TriggerProtocol, platform)


async def async_validate_trigger_config(
    menuai: menuai, config: ConfigType
) -> ConfigType:
    """Validate config."""
    platform = await _async_get_trigger_platform(menuai, config[CONF_PLATFORM])
    if hasattr(platform, "async_validate_trigger_config"):
        return await platform.async_validate_trigger_config(menuai, config)

    return platform.TRIGGER_SCHEMA(config)  # type: ignore[no-any-return]


async def async_attach_trigger(
    menuai: menuai,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach trigger of specified platform."""
    platform = await _async_get_trigger_platform(menuai, config[CONF_PLATFORM])
    return await platform.async_attach_trigger(menuai, config, action, trigger_info)
