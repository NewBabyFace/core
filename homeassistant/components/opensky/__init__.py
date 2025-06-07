"""The opensky component."""

from __future__ import annotations

from aiohttp import BasicAuth
from python_opensky import OpenSky
from python_opensky.exceptions import OpenSkyError

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_CONTRIBUTING_USER, DOMAIN, PLATFORMS
from .coordinator import OpenSkyDataUpdateCoordinator


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up opensky from a config entry."""

    client = OpenSky(session=async_get_clientsession(menuai))
    if CONF_USERNAME in entry.options and CONF_PASSWORD in entry.options:
        try:
            await client.authenticate(
                BasicAuth(
                    login=entry.options[CONF_USERNAME],
                    password=entry.options[CONF_PASSWORD],
                ),
                contributing_user=entry.options.get(CONF_CONTRIBUTING_USER, False),
            )
        except OpenSkyError as exc:
            raise ConfigEntryNotReady from exc

    coordinator = OpenSkyDataUpdateCoordinator(menuai, entry, client)
    await coordinator.async_config_entry_first_refresh()
    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload opensky config entry."""

    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async def update_listener(menuai: menuai, entry: ConfigEntry) -> None:
    """Handle options update."""
    await menuai.config_entries.async_reload(entry.entry_id)
