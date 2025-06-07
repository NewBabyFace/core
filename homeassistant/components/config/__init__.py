"""Component to configure MenuAI via an API."""

from __future__ import annotations

from menuai.components import frontend
from menuai.const import EVENT_COMPONENT_LOADED
from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.typing import ConfigType
from menuai.setup import EventComponentLoaded

from . import (
    area_registry,
    auth,
    auth_provider_menuai,
    automation,
    category_registry,
    config_entries,
    core,
    device_registry,
    entity_registry,
    floor_registry,
    label_registry,
    scene,
    script,
)
from .const import DOMAIN

SECTIONS = (
    area_registry,
    auth,
    auth_provider_menuai,
    automation,
    category_registry,
    config_entries,
    core,
    device_registry,
    entity_registry,
    floor_registry,
    label_registry,
    script,
    scene,
)


CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the config component."""
    frontend.async_register_built_in_panel(
        menuai, "config", "config", "menuai:cog", require_admin=True
    )

    for panel in SECTIONS:
        if panel.async_setup(menuai):
            name = panel.__name__.split(".")[-1]
            key = f"{DOMAIN}.{name}"
            menuai.bus.async_fire(
                EVENT_COMPONENT_LOADED, EventComponentLoaded(component=key)
            )

    return True
