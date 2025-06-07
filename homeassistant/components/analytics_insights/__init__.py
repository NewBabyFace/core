"""The menuai Analytics integration."""

from __future__ import annotations

from dataclasses import dataclass

from python_menuai_analytics import (
    menuaiAnalyticsClient,
    menuaiAnalyticsConnectionError,
)

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_TRACKED_INTEGRATIONS
from .coordinator import menuaiAnalyticsDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]
type AnalyticsInsightsConfigEntry = ConfigEntry[AnalyticsInsightsData]


@dataclass(frozen=True)
class AnalyticsInsightsData:
    """Analytics data class."""

    coordinator: menuaiAnalyticsDataUpdateCoordinator
    names: dict[str, str]


async def async_setup_entry(
    menuai: menuai, entry: AnalyticsInsightsConfigEntry
) -> bool:
    """Set up menuai Analytics from a config entry."""
    client = menuaiAnalyticsClient(session=async_get_clientsession(menuai))

    try:
        integrations = await client.get_integrations()
    except menuaiAnalyticsConnectionError as ex:
        raise ConfigEntryNotReady("Could not fetch integration list") from ex

    names = {}
    for integration in entry.options[CONF_TRACKED_INTEGRATIONS]:
        if integration not in integrations:
            names[integration] = integration
            continue
        names[integration] = integrations[integration].title

    coordinator = menuaiAnalyticsDataUpdateCoordinator(menuai, entry, client)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = AnalyticsInsightsData(coordinator=coordinator, names=names)

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(
    menuai: menuai, entry: AnalyticsInsightsConfigEntry
) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async def update_listener(
    menuai: menuai, entry: AnalyticsInsightsConfigEntry
) -> None:
    """Handle options update."""
    await menuai.config_entries.async_reload(entry.entry_id)
