"""The Traccar Server integration."""

from __future__ import annotations

from datetime import timedelta

from aiohttp import CookieJar
from pytraccar import ApiClient

from menuai.config_entries import ConfigEntry
from menuai.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    Platform,
)
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_create_clientsession
from menuai.helpers.event import async_track_time_interval

from .const import CONF_EVENTS, DOMAIN
from .coordinator import TraccarServerCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.DEVICE_TRACKER,
    Platform.SENSOR,
]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Traccar Server from a config entry."""
    client_session = async_create_clientsession(
        menuai,
        cookie_jar=CookieJar(
            unsafe=not entry.data[CONF_SSL] or not entry.data[CONF_VERIFY_SSL]
        ),
    )
    coordinator = TraccarServerCoordinator(
        menuai=menuai,
        config_entry=entry,
        client=ApiClient(
            client_session=client_session,
            host=entry.data[CONF_HOST],
            port=entry.data[CONF_PORT],
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            ssl=entry.data[CONF_SSL],
            verify_ssl=entry.data[CONF_VERIFY_SSL],
        ),
    )

    await coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})
    menuai.data[DOMAIN][entry.entry_id] = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    if entry.options.get(CONF_EVENTS):
        entry.async_on_unload(
            async_track_time_interval(
                menuai,
                coordinator.import_events,
                timedelta(seconds=30),
                cancel_on_shutdown=True,
                name="traccar_server_import_events",
            )
        )

    entry.async_create_background_task(
        menuai=menuai,
        target=coordinator.subscribe(),
        name="Traccar Server subscription",
    )

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_reload_entry(menuai: menuai, entry: ConfigEntry) -> None:
    """Handle an options update."""
    await menuai.config_entries.async_reload(entry.entry_id)
