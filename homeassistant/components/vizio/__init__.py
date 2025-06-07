"""The vizio component."""

from __future__ import annotations

from typing import Any

from menuai.components.media_player import MediaPlayerDeviceClass
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_DEVICE_CLASS, Platform
from menuai.core import menuai
from menuai.helpers.storage import Store

from .const import CONF_APPS, DOMAIN
from .coordinator import VizioAppsDataUpdateCoordinator

PLATFORMS = [Platform.MEDIA_PLAYER]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Load the saved entities."""

    menuai.data.setdefault(DOMAIN, {})
    if (
        CONF_APPS not in menuai.data[DOMAIN]
        and entry.data[CONF_DEVICE_CLASS] == MediaPlayerDeviceClass.TV
    ):
        store: Store[list[dict[str, Any]]] = Store(menuai, 1, DOMAIN)
        coordinator = VizioAppsDataUpdateCoordinator(menuai, entry, store)
        await coordinator.async_config_entry_first_refresh()
        menuai.data[DOMAIN][CONF_APPS] = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )
    if not any(
        entry.data[CONF_DEVICE_CLASS] == MediaPlayerDeviceClass.TV
        for entry in menuai.config_entries.async_loaded_entries(DOMAIN)
    ):
        menuai.data[DOMAIN].pop(CONF_APPS, None)

    if not menuai.data[DOMAIN]:
        menuai.data.pop(DOMAIN)

    return unload_ok
