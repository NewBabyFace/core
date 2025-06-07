"""Support for functionality to keep track of the sun."""

from __future__ import annotations

import logging

from menuai.config_entries import SOURCE_IMPORT
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.entity_component import EntityComponent
from menuai.helpers.typing import ConfigType

# The sensor platform is pre-imported here to ensure
# it gets loaded when the base component is loaded
# as we will always load it and we do not want to have
# to wait for the import executor when its busy later
# in the startup process.
from . import (
    binary_sensor as binary_sensor_pre_import,  # noqa: F401
    sensor as sensor_pre_import,  # noqa: F401
)
from .const import (  # noqa: F401  # noqa: F401
    DOMAIN,
    STATE_ABOVE_HORIZON,
    STATE_BELOW_HORIZON,
)
from .entity import Sun, SunConfigEntry

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Track the state of the sun."""
    if not menuai.config_entries.async_entries(DOMAIN):
        # We avoid creating an import flow if its already
        # setup since it will have to import the config_flow
        # module.
        menuai.async_create_task(
            menuai.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data=config,
            )
        )
    return True


async def async_setup_entry(menuai: menuai, entry: SunConfigEntry) -> bool:
    """Set up from a config entry."""
    sun = Sun(menuai)
    component = EntityComponent[Sun](_LOGGER, DOMAIN, menuai)
    await component.async_add_entities([sun])
    entry.runtime_data = sun
    entry.async_on_unload(sun.remove_listeners)
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: SunConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.async_remove()
    return unload_ok
