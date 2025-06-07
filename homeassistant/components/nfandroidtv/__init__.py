"""The NFAndroidTV integration."""

from notifications_android_tv.notifications import ConnectError, Notifications

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers import config_validation as cv, discovery
from menuai.helpers.typing import ConfigType

from .const import DATA_menuai_CONFIG, DOMAIN

PLATFORMS = [Platform.NOTIFY]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the NFAndroidTV component."""

    menuai.data[DATA_menuai_CONFIG] = config
    return True


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up NFAndroidTV from a config entry."""
    try:
        await menuai.async_add_executor_job(Notifications, entry.data[CONF_HOST])
    except ConnectError as ex:
        raise ConfigEntryNotReady(
            f"Failed to connect to host: {entry.data[CONF_HOST]}"
        ) from ex

    menuai.data.setdefault(DOMAIN, {})

    menuai.async_create_task(
        discovery.async_load_platform(
            menuai,
            Platform.NOTIFY,
            DOMAIN,
            dict(entry.data),
            menuai.data[DATA_menuai_CONFIG],
        )
    )

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
