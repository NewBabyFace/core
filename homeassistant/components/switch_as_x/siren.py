"""Siren support for switch entities."""

from __future__ import annotations

from menuai.components.siren import (
    DOMAIN as SIREN_DOMAIN,
    SirenEntity,
    SirenEntityFeature,
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
    """Initialize Siren Switch config entry."""
    registry = er.async_get(menuai)
    entity_id = er.async_validate_entity_id(
        registry, config_entry.options[CONF_ENTITY_ID]
    )

    async_add_entities(
        [
            SirenSwitch(
                menuai,
                config_entry.title,
                SIREN_DOMAIN,
                entity_id,
                config_entry.entry_id,
            )
        ]
    )


class SirenSwitch(BaseToggleEntity, SirenEntity):
    """Represents a Switch as a Siren."""

    _attr_supported_features = SirenEntityFeature.TURN_ON | SirenEntityFeature.TURN_OFF
