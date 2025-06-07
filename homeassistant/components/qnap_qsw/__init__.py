"""The QNAP QSW integration."""

from __future__ import annotations

import logging

from aioqsw.localapi import ConnectionOptions, QnapQswApi

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_PASSWORD, CONF_URL, CONF_USERNAME, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers import aiohttp_client

from .const import DOMAIN, QSW_COORD_DATA, QSW_COORD_FW
from .coordinator import QswDataCoordinator, QswFirmwareCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SENSOR,
    Platform.UPDATE,
]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up QNAP QSW from a config entry."""
    options = ConnectionOptions(
        entry.data[CONF_URL],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )

    qsw = QnapQswApi(aiohttp_client.async_get_clientsession(menuai), options)

    coord_data = QswDataCoordinator(menuai, entry, qsw)
    await coord_data.async_config_entry_first_refresh()

    coord_fw = QswFirmwareCoordinator(menuai, entry, qsw)
    try:
        await coord_fw.async_config_entry_first_refresh()
    except ConfigEntryNotReady as error:
        _LOGGER.warning(error)

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        QSW_COORD_DATA: coord_data,
        QSW_COORD_FW: coord_fw,
    }

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
