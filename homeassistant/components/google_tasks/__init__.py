"""The Google Tasks integration."""

from __future__ import annotations

import asyncio

from aiohttp import ClientError, ClientResponseError

from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from menuai.helpers import config_entry_oauth2_flow

from . import api
from .const import DOMAIN
from .coordinator import GoogleTasksConfigEntry, TaskUpdateCoordinator
from .exceptions import GoogleTasksApiError

__all__ = [
    "DOMAIN",
]

PLATFORMS: list[Platform] = [Platform.TODO]


async def async_setup_entry(menuai: menuai, entry: GoogleTasksConfigEntry) -> bool:
    """Set up Google Tasks from a config entry."""
    implementation = (
        await config_entry_oauth2_flow.async_get_config_entry_implementation(
            menuai, entry
        )
    )
    session = config_entry_oauth2_flow.OAuth2Session(menuai, entry, implementation)
    auth = api.AsyncConfigEntryAuth(menuai, session)
    try:
        await auth.async_get_access_token()
    except ClientResponseError as err:
        if 400 <= err.status < 500:
            raise ConfigEntryAuthFailed(
                "OAuth session is not valid, reauth required"
            ) from err
        raise ConfigEntryNotReady from err
    except ClientError as err:
        raise ConfigEntryNotReady from err

    try:
        task_lists = await auth.list_task_lists()
    except GoogleTasksApiError as err:
        raise ConfigEntryNotReady from err

    coordinators = [
        TaskUpdateCoordinator(
            menuai,
            entry,
            auth,
            task_list["id"],
            task_list["title"],
        )
        for task_list in task_lists
    ]
    # Refresh all coordinators in parallel
    await asyncio.gather(
        *(
            coordinator.async_config_entry_first_refresh()
            for coordinator in coordinators
        )
    )
    entry.runtime_data = coordinators

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    menuai: menuai, entry: GoogleTasksConfigEntry
) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
