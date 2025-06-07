"""Support for Axis devices."""

import logging

from menuai.config_entries import ConfigEntry
from menuai.const import EVENT_menuai_STOP
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .const import PLATFORMS
from .errors import AuthenticationRequired, CannotConnect
from .hub import AxisHub, get_axis_api

_LOGGER = logging.getLogger(__name__)

type AxisConfigEntry = ConfigEntry[AxisHub]


async def async_setup_entry(menuai: menuai, config_entry: AxisConfigEntry) -> bool:
    """Set up the Axis integration."""
    try:
        api = await get_axis_api(menuai, config_entry.data)
    except CannotConnect as err:
        raise ConfigEntryNotReady from err
    except AuthenticationRequired as err:
        raise ConfigEntryAuthFailed from err

    hub = config_entry.runtime_data = AxisHub(menuai, config_entry, api)
    await hub.async_update_device_registry()
    await menuai.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    hub.setup()

    config_entry.add_update_listener(hub.async_new_address_callback)
    config_entry.async_on_unload(hub.teardown)
    config_entry.async_on_unload(
        menuai.bus.async_listen_once(EVENT_menuai_STOP, hub.shutdown)
    )

    return True


async def async_unload_entry(menuai: menuai, config_entry: ConfigEntry) -> bool:
    """Unload Axis device config entry."""
    return await menuai.config_entries.async_unload_platforms(config_entry, PLATFORMS)


async def async_migrate_entry(menuai: menuai, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version != 3:
        # MenuAI 2023.2
        menuai.config_entries.async_update_entry(config_entry, version=3)

    _LOGGER.debug("Migration to version %s successful", config_entry.version)

    return True
