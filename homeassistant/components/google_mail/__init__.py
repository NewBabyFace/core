"""Support for Google Mail."""

from __future__ import annotations

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_NAME, Platform
from menuai.core import menuai
from menuai.helpers import config_validation as cv, discovery
from menuai.helpers.config_entry_oauth2_flow import (
    OAuth2Session,
    async_get_config_entry_implementation,
)
from menuai.helpers.typing import ConfigType

from .api import AsyncConfigEntryAuth
from .const import DATA_AUTH, DATA_menuai_CONFIG, DOMAIN
from .services import async_setup_services

type GoogleMailConfigEntry = ConfigEntry[AsyncConfigEntryAuth]

PLATFORMS = [Platform.NOTIFY, Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the Google Mail integration."""
    menuai.data.setdefault(DOMAIN, {})[DATA_menuai_CONFIG] = config

    await async_setup_services(menuai)

    return True


async def async_setup_entry(menuai: menuai, entry: GoogleMailConfigEntry) -> bool:
    """Set up Google Mail from a config entry."""
    implementation = await async_get_config_entry_implementation(menuai, entry)
    session = OAuth2Session(menuai, entry, implementation)
    auth = AsyncConfigEntryAuth(menuai, session)
    await auth.check_and_refresh_token()
    entry.runtime_data = auth

    menuai.async_create_task(
        discovery.async_load_platform(
            menuai,
            Platform.NOTIFY,
            DOMAIN,
            {DATA_AUTH: auth, CONF_NAME: entry.title},
            menuai.data[DOMAIN][DATA_menuai_CONFIG],
        )
    )

    await menuai.config_entries.async_forward_entry_setups(
        entry, [platform for platform in PLATFORMS if platform != Platform.NOTIFY]
    )

    return True


async def async_unload_entry(menuai: menuai, entry: GoogleMailConfigEntry) -> bool:
    """Unload a config entry."""
    if not menuai.config_entries.async_loaded_entries(DOMAIN):
        for service_name in menuai.services.async_services_for_domain(DOMAIN):
            menuai.services.async_remove(DOMAIN, service_name)

    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
