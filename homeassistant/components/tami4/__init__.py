"""The Tami4Edge integration."""

from __future__ import annotations

from Tami4EdgeAPI import Tami4EdgeAPI, exceptions

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryError, ConfigEntryNotReady

from .const import API, CONF_REFRESH_TOKEN, COORDINATOR, DOMAIN
from .coordinator import Tami4EdgeCoordinator

PLATFORMS: list[Platform] = [Platform.BUTTON, Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up tami4 from a config entry."""
    refresh_token = entry.data.get(CONF_REFRESH_TOKEN)

    try:
        api = await menuai.async_add_executor_job(Tami4EdgeAPI, refresh_token)
    except exceptions.RefreshTokenExpiredException as ex:
        raise ConfigEntryError("API Refresh token expired") from ex
    except exceptions.TokenRefreshFailedException as ex:
        raise ConfigEntryNotReady("Error connecting to API") from ex

    coordinator = Tami4EdgeCoordinator(menuai, entry, api)
    await coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        API: api,
        COORDINATOR: coordinator,
    }

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
