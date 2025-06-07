"""The iCloud component."""

from __future__ import annotations

from typing import Any

from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.storage import Store
from menuai.helpers.typing import ConfigType

from .account import IcloudAccount, IcloudConfigEntry
from .const import (
    CONF_GPS_ACCURACY_THRESHOLD,
    CONF_MAX_INTERVAL,
    CONF_WITH_FAMILY,
    DOMAIN,
    PLATFORMS,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .services import async_setup_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up iCloud integration."""

    async_setup_services(menuai)

    return True


async def async_setup_entry(menuai: menuai, entry: IcloudConfigEntry) -> bool:
    """Set up an iCloud account from a config entry."""

    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    with_family = entry.data[CONF_WITH_FAMILY]
    max_interval = entry.data[CONF_MAX_INTERVAL]
    gps_accuracy_threshold = entry.data[CONF_GPS_ACCURACY_THRESHOLD]

    # For backwards compat
    if entry.unique_id is None:
        menuai.config_entries.async_update_entry(entry, unique_id=username)

    icloud_dir = Store[Any](menuai, STORAGE_VERSION, STORAGE_KEY)

    account = IcloudAccount(
        menuai,
        username,
        password,
        icloud_dir,
        with_family,
        max_interval,
        gps_accuracy_threshold,
        entry,
    )
    await menuai.async_add_executor_job(account.setup)

    entry.runtime_data = account

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: IcloudConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
