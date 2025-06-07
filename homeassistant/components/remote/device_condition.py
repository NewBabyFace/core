"""Provides device conditions for remotes."""

from __future__ import annotations

import voluptuous as vol

from menuai.components.device_automation import toggle_entity
from menuai.const import CONF_DOMAIN
from menuai.core import menuai, callback
from menuai.helpers.condition import ConditionCheckerType
from menuai.helpers.typing import ConfigType

from . import DOMAIN

# mypy: disallow-any-generics

CONDITION_SCHEMA = toggle_entity.CONDITION_SCHEMA.extend(
    {vol.Required(CONF_DOMAIN): DOMAIN}
)


@callback
def async_condition_from_config(
    menuai: menuai, config: ConfigType
) -> ConditionCheckerType:
    """Evaluate state based on configuration."""
    return toggle_entity.async_condition_from_config(menuai, config)


async def async_get_conditions(
    menuai: menuai, device_id: str
) -> list[dict[str, str]]:
    """List device conditions."""
    return await toggle_entity.async_get_conditions(menuai, device_id, DOMAIN)


async def async_get_condition_capabilities(
    menuai: menuai, config: ConfigType
) -> dict[str, vol.Schema]:
    """List condition capabilities."""
    return await toggle_entity.async_get_condition_capabilities(menuai, config)
