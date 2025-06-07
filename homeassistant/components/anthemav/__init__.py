"""The Anthem A/V Receivers integration."""

from __future__ import annotations

import logging

import anthemav
from anthemav.device_error import DeviceError

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, CONF_PORT, EVENT_menuai_STOP, Platform
from menuai.core import Event, menuai, callback
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers.dispatcher import async_dispatcher_send

from .const import ANTHEMAV_UPDATE_SIGNAL, DEVICE_TIMEOUT_SECONDS

type AnthemavConfigEntry = ConfigEntry[anthemav.Connection]

PLATFORMS = [Platform.MEDIA_PLAYER]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: AnthemavConfigEntry) -> bool:
    """Set up Anthem A/V Receivers from a config entry."""

    @callback
    def async_anthemav_update_callback(message: str) -> None:
        """Receive notification from transport that new data exists."""
        _LOGGER.debug("Received update callback from AVR: %s", message)
        async_dispatcher_send(menuai, f"{ANTHEMAV_UPDATE_SIGNAL}_{entry.entry_id}")

    try:
        avr = await anthemav.Connection.create(
            host=entry.data[CONF_HOST],
            port=entry.data[CONF_PORT],
            update_callback=async_anthemav_update_callback,
        )

        # Wait for the zones to be initialised based on the model
        await avr.protocol.wait_for_device_initialised(DEVICE_TIMEOUT_SECONDS)
    except (OSError, DeviceError) as err:
        raise ConfigEntryNotReady from err

    entry.runtime_data = avr

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    @callback
    def close_avr(event: Event) -> None:
        avr.close()

    entry.async_on_unload(
        menuai.bus.async_listen_once(EVENT_menuai_STOP, close_avr)
    )

    return True


async def async_unload_entry(menuai: menuai, entry: AnthemavConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)

    avr = entry.runtime_data
    _LOGGER.debug("Close avr connection")
    avr.close()

    return unload_ok
