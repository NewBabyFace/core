"""The Google Photos integration."""

from __future__ import annotations

from aiohttp import ClientError, ClientResponseError
from google_photos_library_api.api import GooglePhotosLibraryApi

from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from menuai.helpers import config_entry_oauth2_flow, config_validation as cv
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.typing import ConfigType

from . import api
from .const import DOMAIN
from .coordinator import GooglePhotosConfigEntry, GooglePhotosUpdateCoordinator
from .services import async_setup_services

__all__ = ["DOMAIN"]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up Google Photos integration."""

    async_setup_services(menuai)

    return True


async def async_setup_entry(
    menuai: menuai, entry: GooglePhotosConfigEntry
) -> bool:
    """Set up Google Photos from a config entry."""
    implementation = (
        await config_entry_oauth2_flow.async_get_config_entry_implementation(
            menuai, entry
        )
    )
    web_session = async_get_clientsession(menuai)
    oauth_session = config_entry_oauth2_flow.OAuth2Session(menuai, entry, implementation)
    auth = api.AsyncConfigEntryAuth(web_session, oauth_session)
    try:
        await auth.async_get_access_token()
    except ClientResponseError as err:
        if 400 <= err.status < 500:
            raise ConfigEntryAuthFailed(
                "OAuth session is not valid, reauth required"
            ) from err
        raise ConfigEntryNotReady from err
    except ClientError as err:
        raise ConfigEntryNotReady from err
    coordinator = GooglePhotosUpdateCoordinator(
        menuai, entry, GooglePhotosLibraryApi(auth)
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    return True


async def async_unload_entry(
    menuai: menuai, entry: GooglePhotosConfigEntry
) -> bool:
    """Unload a config entry."""
    return True
