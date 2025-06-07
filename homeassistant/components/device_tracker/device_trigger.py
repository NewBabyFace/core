"""Provides device automations for Device Tracker."""

from __future__ import annotations

from operator import attrgetter
from typing import Final

import voluptuous as vol

from menuai.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from menuai.components.zone import DOMAIN as DOMAIN_ZONE, trigger as zone
from menuai.const import (
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_ENTITY_ID,
    CONF_EVENT,
    CONF_PLATFORM,
    CONF_TYPE,
    CONF_ZONE,
)
from menuai.core import CALLBACK_TYPE, menuai
from menuai.helpers import config_validation as cv, entity_registry as er
from menuai.helpers.trigger import TriggerActionType, TriggerInfo
from menuai.helpers.typing import ConfigType

from .const import DOMAIN

TRIGGER_TYPES: Final[set[str]] = {"enters", "leaves"}

TRIGGER_SCHEMA: Final = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_ENTITY_ID): cv.entity_id_or_uuid,
        vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
        vol.Required(CONF_ZONE): cv.entity_domain(DOMAIN_ZONE),
    }
)


async def async_get_triggers(
    menuai: menuai, device_id: str
) -> list[dict[str, str]]:
    """List device triggers for Device Tracker devices."""
    registry = er.async_get(menuai)
    triggers = []

    # Get all the integrations entities for this device
    for entry in er.async_entries_for_device(registry, device_id):
        if entry.domain != DOMAIN:
            continue

        triggers.append(
            {
                CONF_PLATFORM: "device",
                CONF_DEVICE_ID: device_id,
                CONF_DOMAIN: DOMAIN,
                CONF_ENTITY_ID: entry.id,
                CONF_TYPE: "enters",
            }
        )
        triggers.append(
            {
                CONF_PLATFORM: "device",
                CONF_DEVICE_ID: device_id,
                CONF_DOMAIN: DOMAIN,
                CONF_ENTITY_ID: entry.id,
                CONF_TYPE: "leaves",
            }
        )

    return triggers


async def async_attach_trigger(
    menuai: menuai,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach a trigger."""
    if config[CONF_TYPE] == "enters":
        event = zone.EVENT_ENTER
    else:
        event = zone.EVENT_LEAVE

    zone_config = {
        CONF_PLATFORM: DOMAIN_ZONE,
        CONF_ENTITY_ID: config[CONF_ENTITY_ID],
        CONF_ZONE: config[CONF_ZONE],
        CONF_EVENT: event,
    }
    zone_config = await zone.async_validate_trigger_config(menuai, zone_config)
    return await zone.async_attach_trigger(
        menuai, zone_config, action, trigger_info, platform_type="device"
    )


async def async_get_trigger_capabilities(
    menuai: menuai, config: ConfigType
) -> dict[str, vol.Schema]:
    """List trigger capabilities."""
    zones = {
        ent.entity_id: ent.name
        for ent in sorted(menuai.states.async_all(DOMAIN_ZONE), key=attrgetter("name"))
    }
    return {
        "extra_fields": vol.Schema(
            {
                vol.Required(CONF_ZONE): vol.In(zones),
            }
        )
    }
