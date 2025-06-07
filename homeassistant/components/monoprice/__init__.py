"""The Monoprice 6-Zone Amplifier integration."""

import logging

from pymonoprice import get_monoprice
from serial import SerialException

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_PORT, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady

from .const import (
    CONF_NOT_FIRST_RUN,
    DOMAIN,
    FIRST_RUN,
    MONOPRICE_OBJECT,
    UNDO_UPDATE_LISTENER,
)

PLATFORMS = [Platform.MEDIA_PLAYER]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Monoprice 6-Zone Amplifier from a config entry."""
    port = entry.data[CONF_PORT]

    try:
        monoprice = await menuai.async_add_executor_job(get_monoprice, port)
    except SerialException as err:
        _LOGGER.error("Error connecting to Monoprice controller at %s", port)
        raise ConfigEntryNotReady from err

    # double negative to handle absence of value
    first_run = not bool(entry.data.get(CONF_NOT_FIRST_RUN))

    if first_run:
        menuai.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_NOT_FIRST_RUN: True}
        )

    undo_listener = entry.add_update_listener(_update_listener)

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        MONOPRICE_OBJECT: monoprice,
        UNDO_UPDATE_LISTENER: undo_listener,
        FIRST_RUN: first_run,
    }

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    menuai.data[DOMAIN][entry.entry_id][UNDO_UPDATE_LISTENER]()

    def _cleanup(monoprice) -> None:
        """Destroy the Monoprice object.

        Destroying the Monoprice closes the serial connection, do it in an executor so the garbage
        collection does not block.
        """
        del monoprice

    monoprice = menuai.data[DOMAIN][entry.entry_id][MONOPRICE_OBJECT]
    menuai.data[DOMAIN].pop(entry.entry_id)

    await menuai.async_add_executor_job(_cleanup, monoprice)

    return True


async def _update_listener(menuai: menuai, entry: ConfigEntry) -> None:
    """Handle options update."""
    await menuai.config_entries.async_reload(entry.entry_id)
