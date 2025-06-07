"""The EnergyZero integration."""

from __future__ import annotations

from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers import config_validation as cv
from menuai.helpers.typing import ConfigType

from .const import DOMAIN
from .coordinator import EnergyZeroConfigEntry, EnergyZeroDataUpdateCoordinator
from .services import async_setup_services

PLATFORMS: list[Platform] = [Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up EnergyZero services."""

    async_setup_services(menuai)

    return True


async def async_setup_entry(menuai: menuai, entry: EnergyZeroConfigEntry) -> bool:
    """Set up EnergyZero from a config entry."""

    coordinator = EnergyZeroDataUpdateCoordinator(menuai, entry)
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        await coordinator.energyzero.close()
        raise

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: EnergyZeroConfigEntry) -> bool:
    """Unload EnergyZero config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
