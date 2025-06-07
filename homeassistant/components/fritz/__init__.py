"""Support for AVM Fritz!Box functions."""

import logging

from menuai.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
)
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from menuai.helpers import config_validation as cv
from menuai.helpers.typing import ConfigType

from .const import (
    CONF_FEATURE_DEVICE_TRACKING,
    DEFAULT_CONF_FEATURE_DEVICE_TRACKING,
    DEFAULT_SSL,
    DOMAIN,
    FRITZ_AUTH_EXCEPTIONS,
    FRITZ_EXCEPTIONS,
    PLATFORMS,
)
from .coordinator import FRITZ_DATA_KEY, AvmWrapper, FritzConfigEntry, FritzData
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up fritzboxtools integration."""
    await async_setup_services(menuai)
    return True


async def async_setup_entry(menuai: menuai, entry: FritzConfigEntry) -> bool:
    """Set up fritzboxtools from config entry."""
    _LOGGER.debug("Setting up FRITZ!Box Tools component")

    avm_wrapper = AvmWrapper(
        menuai=menuai,
        config_entry=entry,
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        use_tls=entry.data.get(CONF_SSL, DEFAULT_SSL),
        device_discovery_enabled=entry.options.get(
            CONF_FEATURE_DEVICE_TRACKING, DEFAULT_CONF_FEATURE_DEVICE_TRACKING
        ),
    )

    try:
        await avm_wrapper.async_setup(entry.options)
    except FRITZ_AUTH_EXCEPTIONS as ex:
        raise ConfigEntryAuthFailed from ex
    except FRITZ_EXCEPTIONS as ex:
        raise ConfigEntryNotReady from ex

    if (
        "X_AVM-DE_UPnP1" in avm_wrapper.connection.services
        and not (await avm_wrapper.async_get_upnp_configuration())["NewEnable"]
    ):
        raise ConfigEntryAuthFailed("Missing UPnP configuration")

    await avm_wrapper.async_config_entry_first_refresh()
    await avm_wrapper.async_trigger_cleanup()

    entry.runtime_data = avm_wrapper

    if FRITZ_DATA_KEY not in menuai.data:
        menuai.data[FRITZ_DATA_KEY] = FritzData()

    entry.async_on_unload(entry.add_update_listener(update_listener))

    # Load the other platforms like switch
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: FritzConfigEntry) -> bool:
    """Unload FRITZ!Box Tools config entry."""
    avm_wrapper = entry.runtime_data

    fritz_data = menuai.data[FRITZ_DATA_KEY]
    fritz_data.tracked.pop(avm_wrapper.unique_id)

    if not bool(fritz_data.tracked):
        menuai.data.pop(FRITZ_DATA_KEY)

    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async def update_listener(menuai: menuai, entry: FritzConfigEntry) -> None:
    """Update when config_entry options update."""
    if entry.options:
        await menuai.config_entries.async_reload(entry.entry_id)
