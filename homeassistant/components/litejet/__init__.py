"""Support for the LiteJet lighting system."""

import logging

import pylitejet

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_PORT, EVENT_menuai_STOP
from menuai.core import Event, menuai
from menuai.exceptions import ConfigEntryNotReady

from .const import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up LiteJet via a config entry."""
    port = entry.data[CONF_PORT]

    try:
        system = await pylitejet.open(port)
    except pylitejet.LiteJetError as exc:
        raise ConfigEntryNotReady from exc

    def handle_connected_changed(connected: bool, reason: str) -> None:
        if connected:
            _LOGGER.debug("Connected")
        else:
            _LOGGER.warning("Disconnected %s", reason)

    system.on_connected_changed(handle_connected_changed)

    async def handle_stop(event: Event) -> None:
        await system.close()

    entry.async_on_unload(
        menuai.bus.async_listen_once(EVENT_menuai_STOP, handle_stop)
    )

    menuai.data[DOMAIN] = system

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a LiteJet config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        await menuai.data[DOMAIN].close()
        menuai.data.pop(DOMAIN)

    return unload_ok
