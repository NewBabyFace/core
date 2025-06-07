"""Provide the device automations for Humidifier."""

from __future__ import annotations

import voluptuous as vol

from menuai.components.device_automation import (
    async_get_entity_registry_entry_or_raise,
    toggle_entity,
)
from menuai.const import (
    ATTR_ENTITY_ID,
    ATTR_MODE,
    CONF_CONDITION,
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_ENTITY_ID,
    CONF_TYPE,
)
from menuai.core import menuai, callback
from menuai.exceptions import menuaiError
from menuai.helpers import (
    condition,
    config_validation as cv,
    entity_registry as er,
)
from menuai.helpers.config_validation import DEVICE_CONDITION_BASE_SCHEMA
from menuai.helpers.entity import get_capability, get_supported_features
from menuai.helpers.typing import ConfigType, TemplateVarsType

from . import DOMAIN, const

TOGGLE_CONDITION = toggle_entity.CONDITION_SCHEMA.extend(
    {vol.Required(CONF_DOMAIN): DOMAIN}
)

MODE_CONDITION = DEVICE_CONDITION_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_ENTITY_ID): cv.entity_id_or_uuid,
        vol.Required(CONF_TYPE): "is_mode",
        vol.Required(ATTR_MODE): str,
    }
)

CONDITION_SCHEMA = vol.Any(TOGGLE_CONDITION, MODE_CONDITION)


async def async_get_conditions(
    menuai: menuai, device_id: str
) -> list[dict[str, str]]:
    """List device conditions for Humidifier devices."""
    registry = er.async_get(menuai)
    conditions = await toggle_entity.async_get_conditions(menuai, device_id, DOMAIN)

    # Get all the integrations entities for this device
    for entry in er.async_entries_for_device(registry, device_id):
        if entry.domain != DOMAIN:
            continue

        supported_features = get_supported_features(menuai, entry.entity_id)

        if supported_features & const.HumidifierEntityFeature.MODES:
            conditions.append(
                {
                    CONF_CONDITION: "device",
                    CONF_DEVICE_ID: device_id,
                    CONF_DOMAIN: DOMAIN,
                    CONF_ENTITY_ID: entry.id,
                    CONF_TYPE: "is_mode",
                }
            )

    return conditions


@callback
def async_condition_from_config(
    menuai: menuai, config: ConfigType
) -> condition.ConditionCheckerType:
    """Create a function to test a device condition."""
    if config[CONF_TYPE] == "is_mode":
        attribute = ATTR_MODE
    else:
        return toggle_entity.async_condition_from_config(menuai, config)

    registry = er.async_get(menuai)
    entity_id = er.async_resolve_entity_id(registry, config[ATTR_ENTITY_ID])

    def test_is_state(menuai: menuai, variables: TemplateVarsType) -> bool:
        """Test if an entity is a certain state."""
        return (
            entity_id is not None
            and (state := menuai.states.get(entity_id)) is not None
            and state.attributes.get(attribute) == config[attribute]
        )

    return test_is_state


async def async_get_condition_capabilities(
    menuai: menuai, config: ConfigType
) -> dict[str, vol.Schema]:
    """List condition capabilities."""
    condition_type = config[CONF_TYPE]

    fields = {}

    if condition_type == "is_mode":
        try:
            entry = async_get_entity_registry_entry_or_raise(
                menuai, config[CONF_ENTITY_ID]
            )
            modes = (
                get_capability(menuai, entry.entity_id, const.ATTR_AVAILABLE_MODES) or []
            )
        except menuaiError:
            modes = []

        fields[vol.Required(ATTR_MODE)] = vol.In(modes)

        return {"extra_fields": vol.Schema(fields)}

    return await toggle_entity.async_get_condition_capabilities(menuai, config)
