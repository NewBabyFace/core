"""The Weheat integration."""

from __future__ import annotations

import asyncio
from http import HTTPStatus

import aiohttp
from weheat.abstractions.discovery import HeatPumpDiscovery
from weheat.exceptions import UnauthorizedException

from menuai.const import CONF_ACCESS_TOKEN, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.config_entry_oauth2_flow import (
    OAuth2Session,
    async_get_config_entry_implementation,
)

from .const import API_URL, LOGGER
from .coordinator import (
    HeatPumpInfo,
    WeheatConfigEntry,
    WeheatData,
    WeheatDataUpdateCoordinator,
    WeheatEnergyUpdateCoordinator,
)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: WeheatConfigEntry) -> bool:
    """Set up Weheat from a config entry."""
    implementation = await async_get_config_entry_implementation(menuai, entry)

    session = OAuth2Session(menuai, entry, implementation)

    try:
        await session.async_ensure_token_valid()
    except aiohttp.ClientResponseError as ex:
        LOGGER.warning("API error: %s (%s)", ex.status, ex.message)
        if ex.status in (
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.UNAUTHORIZED,
            HTTPStatus.FORBIDDEN,
        ):
            raise ConfigEntryAuthFailed("Token not valid, trigger renewal") from ex
        raise ConfigEntryNotReady from ex

    token = session.token[CONF_ACCESS_TOKEN]
    entry.runtime_data = []

    # fetch a list of the heat pumps the entry can access
    try:
        discovered_heat_pumps = await HeatPumpDiscovery.async_discover_active(
            API_URL, token, async_get_clientsession(menuai)
        )
    except UnauthorizedException as error:
        raise ConfigEntryAuthFailed from error

    nr_of_pumps = len(discovered_heat_pumps)

    for pump_info in discovered_heat_pumps:
        LOGGER.debug("Adding %s", pump_info)
        # for each pump, add the coordinators

        new_heat_pump = HeatPumpInfo(pump_info)
        new_data_coordinator = WeheatDataUpdateCoordinator(
            menuai, entry, session, pump_info, nr_of_pumps
        )
        new_energy_coordinator = WeheatEnergyUpdateCoordinator(
            menuai, entry, session, pump_info
        )

        entry.runtime_data.append(
            WeheatData(
                heat_pump_info=new_heat_pump,
                data_coordinator=new_data_coordinator,
                energy_coordinator=new_energy_coordinator,
            )
        )

    await asyncio.gather(
        *[
            data.data_coordinator.async_config_entry_first_refresh()
            for data in entry.runtime_data
        ],
        *[
            data.energy_coordinator.async_config_entry_first_refresh()
            for data in entry.runtime_data
        ],
    )

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: WeheatConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
