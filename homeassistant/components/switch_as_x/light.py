"""Light support for switch entities."""

from __future__ import annotations

from menuai.components.light import (
    DOMAIN as LIGHT_DOMAIN,
    ColorMode,
    LightEntity,
)
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_ENTITY_ID
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import BaseToggleEntity


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Initialize Light Switch config entry."""
    registry = er.async_get(menuai)
    entity_id = er.async_validate_entity_id(
        registry, config_entry.options[CONF_ENTITY_ID]
    )

    async_add_entities(
        [
            LightSwitch(
                menuai,
                config_entry.title,
                LIGHT_DOMAIN,
                entity_id,
                config_entry.entry_id,
            )
        ]
    )


class LightSwitch(BaseToggleEntity, LightEntity):
    """Represents a Switch as a Light."""

    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}
