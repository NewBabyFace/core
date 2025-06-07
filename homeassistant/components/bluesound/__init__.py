"""The bluesound component."""

from pyblu import Player
from pyblu.errors import PlayerUnreachableError

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, CONF_PORT, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers import config_validation as cv
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.typing import ConfigType

from .const import DOMAIN
from .coordinator import (
    BluesoundConfigEntry,
    BluesoundCoordinator,
    BluesoundRuntimeData,
)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS = [
    Platform.BUTTON,
    Platform.MEDIA_PLAYER,
]


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the Bluesound."""
    return True


async def async_setup_entry(
    menuai: menuai, config_entry: BluesoundConfigEntry
) -> bool:
    """Set up the Bluesound entry."""
    host = config_entry.data[CONF_HOST]
    port = config_entry.data[CONF_PORT]
    session = async_get_clientsession(menuai)
    player = Player(host, port, session=session, default_timeout=10)
    try:
        sync_status = await player.sync_status(timeout=1)
    except PlayerUnreachableError as ex:
        raise ConfigEntryNotReady(f"Error connecting to {host}:{port}") from ex

    coordinator = BluesoundCoordinator(menuai, config_entry, player, sync_status)
    await coordinator.async_config_entry_first_refresh()

    config_entry.runtime_data = BluesoundRuntimeData(player, sync_status, coordinator)

    await menuai.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(config_entry, PLATFORMS)
