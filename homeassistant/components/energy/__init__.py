"""The Energy integration."""

from __future__ import annotations

from menuai.components import frontend
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import config_validation as cv, discovery
from menuai.helpers.typing import ConfigType

from . import websocket_api
from .const import DOMAIN
from .data import async_get_manager

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def is_configured(menuai: menuai) -> bool:
    """Return a boolean to indicate if energy is configured."""
    manager = await async_get_manager(menuai)
    if manager.data is None:
        return False
    return bool(manager.data != manager.default_preferences())


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up Energy."""
    websocket_api.async_setup(menuai)
    frontend.async_register_built_in_panel(menuai, DOMAIN, DOMAIN, "mdi:lightning-bolt")

    menuai.async_create_task(
        discovery.async_load_platform(menuai, Platform.SENSOR, DOMAIN, {}, config),
        eager_start=True,
    )
    menuai.data[DOMAIN] = {
        "cost_sensors": {},
    }

    return True
