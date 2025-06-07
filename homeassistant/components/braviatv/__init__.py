"""The Bravia TV integration."""

from __future__ import annotations

from typing import Final

from aiohttp import CookieJar
from pybravia import BraviaClient

from menuai.const import CONF_HOST, CONF_MAC, Platform
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_create_clientsession

from .coordinator import BraviaTVConfigEntry, BraviaTVCoordinator

PLATFORMS: Final[list[Platform]] = [
    Platform.BUTTON,
    Platform.MEDIA_PLAYER,
    Platform.REMOTE,
]


async def async_setup_entry(
    menuai: menuai, config_entry: BraviaTVConfigEntry
) -> bool:
    """Set up a config entry."""
    host = config_entry.data[CONF_HOST]
    mac = config_entry.data[CONF_MAC]

    session = async_create_clientsession(
        menuai, cookie_jar=CookieJar(unsafe=True, quote_cookie=False)
    )
    client = BraviaClient(host, mac, session=session)
    coordinator = BraviaTVCoordinator(
        menuai=menuai,
        config_entry=config_entry,
        client=client,
    )
    config_entry.async_on_unload(config_entry.add_update_listener(update_listener))

    await coordinator.async_config_entry_first_refresh()

    config_entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True


async def async_unload_entry(
    menuai: menuai, config_entry: BraviaTVConfigEntry
) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(config_entry, PLATFORMS)


async def update_listener(
    menuai: menuai, config_entry: BraviaTVConfigEntry
) -> None:
    """Handle options update."""
    await menuai.config_entries.async_reload(config_entry.entry_id)
