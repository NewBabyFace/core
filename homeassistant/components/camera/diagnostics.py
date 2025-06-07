"""Diagnostics for camera."""

from typing import Any

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er

from .const import DOMAIN
from .helper import get_camera_from_entity_id


async def async_get_config_entry_diagnostics(
    menuai: menuai, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    entity_registry = er.async_get(menuai)
    entities = er.async_entries_for_config_entry(entity_registry, config_entry.entry_id)
    diagnostics = {}
    for entity in entities:
        if entity.domain != DOMAIN:
            continue
        try:
            camera = get_camera_from_entity_id(menuai, entity.entity_id)
        except menuaiError:
            continue
        diagnostics[entity.entity_id] = (
            camera.stream.get_diagnostics() if camera.stream else {}
        )
    return diagnostics
