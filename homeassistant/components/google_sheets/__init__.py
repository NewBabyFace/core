"""Support for Google Sheets."""

from __future__ import annotations

import aiohttp

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_TOKEN
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from menuai.helpers import config_validation as cv
from menuai.helpers.config_entry_oauth2_flow import (
    OAuth2Session,
    async_get_config_entry_implementation,
)
from menuai.helpers.typing import ConfigType

from .const import DEFAULT_ACCESS, DOMAIN
from .services import async_setup_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type GoogleSheetsConfigEntry = ConfigEntry[OAuth2Session]


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Activate the Google Sheets component."""

    async_setup_services(menuai)

    return True


async def async_setup_entry(
    menuai: menuai, entry: GoogleSheetsConfigEntry
) -> bool:
    """Set up Google Sheets from a config entry."""
    implementation = await async_get_config_entry_implementation(menuai, entry)
    session = OAuth2Session(menuai, entry, implementation)
    try:
        await session.async_ensure_token_valid()
    except aiohttp.ClientResponseError as err:
        if 400 <= err.status < 500:
            raise ConfigEntryAuthFailed(
                "OAuth session is not valid, reauth required"
            ) from err
        raise ConfigEntryNotReady from err
    except aiohttp.ClientError as err:
        raise ConfigEntryNotReady from err

    if not async_entry_has_scopes(menuai, entry):
        raise ConfigEntryAuthFailed("Required scopes are not present, reauth required")
    entry.runtime_data = session

    return True


def async_entry_has_scopes(menuai: menuai, entry: GoogleSheetsConfigEntry) -> bool:
    """Verify that the config entry desired scope is present in the oauth token."""
    return DEFAULT_ACCESS in entry.data.get(CONF_TOKEN, {}).get("scope", "").split(" ")


async def async_unload_entry(
    menuai: menuai, entry: GoogleSheetsConfigEntry
) -> bool:
    """Unload a config entry."""
    return True
