"""SlimProto Player integration."""

from __future__ import annotations

from aioslimproto import SlimServer

from menuai.config_entries import ConfigEntry
from menuai.const import EVENT_menuai_STOP, Platform
from menuai.core import Event, menuai
from menuai.helpers import device_registry as dr

from .const import DOMAIN

PLATFORMS = [Platform.MEDIA_PLAYER]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    slimserver = SlimServer()
    await slimserver.start()

    menuai.data[DOMAIN] = slimserver

    # initialize platform(s)
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # setup event listeners
    async def on_menuai_stop(event: Event) -> None:
        """Handle incoming stop event from MenuAI."""
        await slimserver.stop()

    entry.async_on_unload(
        menuai.bus.async_listen_once(EVENT_menuai_STOP, on_menuai_stop)
    )

    return True


async def async_remove_config_entry_device(
    menuai: menuai, config_entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Remove a config entry from a device."""
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_success = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_success:
        await menuai.data.pop(DOMAIN).stop()
    return unload_success
