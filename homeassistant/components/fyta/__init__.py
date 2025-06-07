"""Initialization of FYTA integration."""

from __future__ import annotations

from datetime import datetime
import logging

from fyta_cli.fyta_connector import FytaConnector

from menuai.const import (
    CONF_ACCESS_TOKEN,
    CONF_PASSWORD,
    CONF_USERNAME,
    Platform,
)
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.util.dt import async_get_time_zone

from .const import CONF_EXPIRATION
from .coordinator import FytaConfigEntry, FytaCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.IMAGE,
    Platform.SENSOR,
]


async def async_setup_entry(menuai: menuai, entry: FytaConfigEntry) -> bool:
    """Set up the Fyta integration."""
    tz: str = menuai.config.time_zone

    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    access_token: str = entry.data[CONF_ACCESS_TOKEN]
    expiration: datetime = datetime.fromisoformat(
        entry.data[CONF_EXPIRATION]
    ).astimezone(await async_get_time_zone(tz))

    fyta = FytaConnector(
        username, password, access_token, expiration, tz, async_get_clientsession(menuai)
    )

    coordinator = FytaCoordinator(menuai, entry, fyta)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: FytaConfigEntry) -> bool:
    """Unload Fyta entity."""

    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(
    menuai: menuai, config_entry: FytaConfigEntry
) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version > 1:
        # This means the user has downgraded from a future version
        return False

    if config_entry.version == 1:
        if config_entry.minor_version < 2:
            new = {**config_entry.data}
            fyta = FytaConnector(
                config_entry.data[CONF_USERNAME], config_entry.data[CONF_PASSWORD]
            )
            credentials = await fyta.login()
            await fyta.client.close()

            new[CONF_ACCESS_TOKEN] = credentials.access_token
            new[CONF_EXPIRATION] = credentials.expiration.isoformat()

            menuai.config_entries.async_update_entry(
                config_entry,
                data=new,
                minor_version=2,
                version=1,
            )

    _LOGGER.debug(
        "Migration to version %s.%s successful",
        config_entry.version,
        config_entry.minor_version,
    )

    return True
