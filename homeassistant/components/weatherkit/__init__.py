"""Integration for Apple's WeatherKit API."""

from __future__ import annotations

from apple_weatherkit.client import (
    WeatherKitApiClient,
    WeatherKitApiClientAuthenticationError,
    WeatherKitApiClientError,
)

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_KEY_ID,
    CONF_KEY_PEM,
    CONF_SERVICE_ID,
    CONF_TEAM_ID,
    DOMAIN,
    LOGGER,
)
from .coordinator import WeatherKitDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.WEATHER]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    menuai.data.setdefault(DOMAIN, {})
    coordinator = WeatherKitDataUpdateCoordinator(
        menuai=menuai,
        config_entry=entry,
        client=WeatherKitApiClient(
            key_id=entry.data[CONF_KEY_ID],
            service_id=entry.data[CONF_SERVICE_ID],
            team_id=entry.data[CONF_TEAM_ID],
            key_pem=entry.data[CONF_KEY_PEM],
            session=async_get_clientsession(menuai),
        ),
    )

    try:
        await coordinator.update_supported_data_sets()
    except WeatherKitApiClientAuthenticationError as ex:
        LOGGER.error("Authentication error initializing integration: %s", ex)
        return False
    except WeatherKitApiClientError as ex:
        raise ConfigEntryNotReady from ex

    await coordinator.async_config_entry_first_refresh()
    menuai.data[DOMAIN][entry.entry_id] = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    if unloaded := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)
    return unloaded
