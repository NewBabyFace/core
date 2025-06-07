"""The Livisi Smart Home integration."""

from __future__ import annotations

from typing import Final

from aiohttp import ClientConnectorError
from livisi.aiolivisi import AioLivisi

from menuai import core
from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers import aiohttp_client, device_registry as dr

from .const import DOMAIN
from .coordinator import LivisiDataUpdateCoordinator

PLATFORMS: Final = [Platform.BINARY_SENSOR, Platform.CLIMATE, Platform.SWITCH]


async def async_setup_entry(menuai: core.menuai, entry: ConfigEntry) -> bool:
    """Set up Livisi Smart Home from a config entry."""
    web_session = aiohttp_client.async_get_clientsession(menuai)
    aiolivisi = AioLivisi(web_session)
    coordinator = LivisiDataUpdateCoordinator(menuai, entry, aiolivisi)
    try:
        await coordinator.async_setup()
        await coordinator.async_set_all_rooms()
    except ClientConnectorError as exception:
        raise ConfigEntryNotReady from exception

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    device_registry = dr.async_get(menuai)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer="Livisi",
        name=f"SHC {coordinator.controller_type} {coordinator.serial_number}",
    )

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await coordinator.async_config_entry_first_refresh()
    entry.async_create_background_task(
        menuai, coordinator.ws_connect(), "livisi-ws_connect"
    )
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator = menuai.data[DOMAIN][entry.entry_id]

    unload_success = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    await coordinator.websocket.disconnect()
    if unload_success:
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_success
