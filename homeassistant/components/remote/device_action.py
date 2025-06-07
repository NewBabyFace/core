"""Provides device actions for remotes."""

from __future__ import annotations

import voluptuous as vol

from menuai.components.device_automation import (
    async_validate_entity_schema,
    toggle_entity,
)
from menuai.const import CONF_DOMAIN
from menuai.core import Context, menuai
from menuai.helpers.typing import ConfigType, TemplateVarsType

from . import DOMAIN

# mypy: disallow-any-generics

_ACTION_SCHEMA = toggle_entity.ACTION_SCHEMA.extend({vol.Required(CONF_DOMAIN): DOMAIN})


async def async_validate_action_config(
    menuai: menuai, config: ConfigType
) -> ConfigType:
    """Validate config."""
    return async_validate_entity_schema(menuai, config, _ACTION_SCHEMA)


async def async_call_action_from_config(
    menuai: menuai,
    config: ConfigType,
    variables: TemplateVarsType,
    context: Context | None,
) -> None:
    """Change state based on configuration."""
    await toggle_entity.async_call_action_from_config(
        menuai, config, variables, context, DOMAIN
    )


async def async_get_actions(
    menuai: menuai, device_id: str
) -> list[dict[str, str]]:
    """List device actions."""
    return await toggle_entity.async_get_actions(menuai, device_id, DOMAIN)
