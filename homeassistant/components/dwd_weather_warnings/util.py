"""Util functions for the dwd_weather_warnings integration."""

from __future__ import annotations

from menuai.const import ATTR_LATITUDE, ATTR_LONGITUDE
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .exceptions import EntityNotFoundError


def get_position_data(
    menuai: menuai, registry_id: str
) -> tuple[float, float] | None:
    """Extract longitude and latitude from a device tracker."""
    registry = er.async_get(menuai)
    registry_entry = registry.async_get(registry_id)
    if registry_entry is None:
        raise EntityNotFoundError(f"Failed to find registry entry {registry_id}")

    entity = menuai.states.get(registry_entry.entity_id)
    if entity is None:
        raise EntityNotFoundError(f"Failed to find entity {registry_entry.entity_id}")

    latitude = entity.attributes.get(ATTR_LATITUDE)
    if not latitude:
        raise AttributeError(
            f"Failed to find attribute '{ATTR_LATITUDE}' in {registry_entry.entity_id}",
            ATTR_LATITUDE,
        )

    longitude = entity.attributes.get(ATTR_LONGITUDE)
    if not longitude:
        raise AttributeError(
            f"Failed to find attribute '{ATTR_LONGITUDE}' in {registry_entry.entity_id}",
            ATTR_LONGITUDE,
        )

    return (latitude, longitude)
