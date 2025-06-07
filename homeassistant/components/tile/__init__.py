"""The Tile component."""

from __future__ import annotations

from pytile import async_login
from pytile.errors import InvalidAuthError, TileError

from menuai.const import CONF_PASSWORD, CONF_USERNAME, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from menuai.helpers import aiohttp_client
from menuai.util.async_ import gather_with_limited_concurrency

from .coordinator import TileConfigEntry, TileCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.DEVICE_TRACKER]
DEVICE_TYPES = ["PHONE", "TILE"]

DEFAULT_INIT_TASK_LIMIT = 2

CONF_SHOW_INACTIVE = "show_inactive"


async def async_setup_entry(menuai: menuai, entry: TileConfigEntry) -> bool:
    """Set up Tile as config entry."""

    # Tile's API uses cookies to identify a consumer; in order to allow for multiple
    # instances of this config entry, we use a new session each time:
    websession = aiohttp_client.async_create_clientsession(menuai)

    try:
        client = await async_login(
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
            session=websession,
        )
        tiles = await client.async_get_tiles()
    except InvalidAuthError as err:
        raise ConfigEntryAuthFailed("Invalid credentials") from err
    except TileError as err:
        raise ConfigEntryNotReady("Error during integration setup") from err

    coordinators: dict[str, TileCoordinator] = {}
    coordinator_init_tasks = []

    for tile_uuid, tile in tiles.items():
        coordinator = coordinators[tile_uuid] = TileCoordinator(
            menuai, entry, client, tile
        )
        coordinator_init_tasks.append(coordinator.async_refresh())

    await gather_with_limited_concurrency(
        DEFAULT_INIT_TASK_LIMIT, *coordinator_init_tasks
    )
    entry.runtime_data = coordinators

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: TileConfigEntry) -> bool:
    """Unload a Tile config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
