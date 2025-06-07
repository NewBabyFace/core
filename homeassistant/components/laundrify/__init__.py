"""The laundrify integration."""

from __future__ import annotations

import logging

from laundrify_aio import LaundrifyAPI
from laundrify_aio.exceptions import ApiConnectionException, UnauthorizedException

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_ACCESS_TOKEN, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from menuai.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .coordinator import LaundrifyUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up laundrify from a config entry."""

    session = async_get_clientsession(menuai)
    api_client = LaundrifyAPI(entry.data[CONF_ACCESS_TOKEN], session)

    try:
        await api_client.validate_token()
    except UnauthorizedException as err:
        raise ConfigEntryAuthFailed("Invalid authentication") from err
    except ApiConnectionException as err:
        raise ConfigEntryNotReady("Cannot reach laundrify API") from err

    coordinator = LaundrifyUpdateCoordinator(menuai, entry, api_client)

    await coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api": api_client,
        "coordinator": coordinator,
    }

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_migrate_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Migrate entry."""

    _LOGGER.debug("Migrating from version %s", entry.version)

    if entry.version == 1:
        # 1 -> 2: Unique ID from integer to string
        if entry.minor_version == 1:
            minor_version = 2
            menuai.config_entries.async_update_entry(
                entry, unique_id=str(entry.unique_id), minor_version=minor_version
            )

    _LOGGER.debug("Migration successful")

    return True
