"""The MusicCast integration."""

from __future__ import annotations

import logging

from aiomusiccast.musiccast_device import MusicCastDevice

from menuai.components import ssdp
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, Platform
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_SERIAL, CONF_UPNP_DESC, DOMAIN
from .coordinator import MusicCastDataUpdateCoordinator

PLATFORMS = [Platform.MEDIA_PLAYER, Platform.NUMBER, Platform.SELECT, Platform.SWITCH]

_LOGGER = logging.getLogger(__name__)


async def get_upnp_desc(menuai: menuai, host: str):
    """Get the upnp description URL for a given host, using the SSPD scanner."""
    ssdp_entries = await ssdp.async_get_discovery_info_by_st(menuai, "upnp:rootdevice")
    matches = [w for w in ssdp_entries if w.ssdp_headers.get("_host", "") == host]
    upnp_desc = None
    for match in matches:
        if upnp_desc := match.ssdp_location:
            break

    if not upnp_desc:
        _LOGGER.warning(
            "The upnp_description was not found automatically, setting a default one"
        )
        upnp_desc = f"http://{host}:49154/MediaRenderer/desc.xml"
    return upnp_desc


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up MusicCast from a config entry."""

    if entry.data.get(CONF_UPNP_DESC) is None:
        menuai.config_entries.async_update_entry(
            entry,
            data={
                CONF_HOST: entry.data[CONF_HOST],
                CONF_SERIAL: entry.data["serial"],
                CONF_UPNP_DESC: await get_upnp_desc(menuai, entry.data[CONF_HOST]),
            },
        )

    client = MusicCastDevice(
        entry.data[CONF_HOST],
        async_get_clientsession(menuai),
        entry.data[CONF_UPNP_DESC],
    )
    coordinator = MusicCastDataUpdateCoordinator(menuai, entry, client=client)
    await coordinator.async_config_entry_first_refresh()
    coordinator.musiccast.build_capabilities()

    menuai.data.setdefault(DOMAIN, {})
    menuai.data[DOMAIN][entry.entry_id] = coordinator

    await coordinator.musiccast.device.enable_polling()

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        menuai.data[DOMAIN][entry.entry_id].musiccast.device.disable_polling()
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(menuai: menuai, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await menuai.config_entries.async_reload(entry.entry_id)
