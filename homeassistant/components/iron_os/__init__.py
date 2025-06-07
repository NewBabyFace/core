"""The IronOS integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pynecil import IronOSUpdate, Pynecil

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.typing import ConfigType
from menuai.util.menuai_dict import menuaiKey

from .const import DOMAIN
from .coordinator import (
    IronOSConfigEntry,
    IronOSCoordinators,
    IronOSFirmwareUpdateCoordinator,
    IronOSLiveDataCoordinator,
    IronOSSettingsCoordinator,
)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.UPDATE,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


IRON_OS_KEY: menuaiKey[IronOSFirmwareUpdateCoordinator] = menuaiKey(DOMAIN)


_LOGGER = logging.getLogger(__name__)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up IronOS firmware update coordinator."""

    session = async_get_clientsession(menuai)
    github = IronOSUpdate(session)

    menuai.data[IRON_OS_KEY] = IronOSFirmwareUpdateCoordinator(menuai, github)
    await menuai.data[IRON_OS_KEY].async_request_refresh()
    return True


async def async_setup_entry(menuai: menuai, entry: IronOSConfigEntry) -> bool:
    """Set up IronOS from a config entry."""
    if TYPE_CHECKING:
        assert entry.unique_id

    device = Pynecil(entry.unique_id)

    live_data = IronOSLiveDataCoordinator(menuai, entry, device)
    await live_data.async_config_entry_first_refresh()

    settings = IronOSSettingsCoordinator(menuai, entry, device)
    await settings.async_config_entry_first_refresh()

    entry.runtime_data = IronOSCoordinators(
        live_data=live_data,
        settings=settings,
    )
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: IronOSConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
