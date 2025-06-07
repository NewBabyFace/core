"""The Google Drive integration."""

from __future__ import annotations

from collections.abc import Callable

from google_drive_api.exceptions import GoogleDriveApiError

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers import instance_id
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.config_entry_oauth2_flow import (
    OAuth2Session,
    async_get_config_entry_implementation,
)
from menuai.util.menuai_dict import menuaiKey

from .api import AsyncConfigEntryAuth, DriveClient
from .const import DOMAIN

DATA_BACKUP_AGENT_LISTENERS: menuaiKey[list[Callable[[], None]]] = menuaiKey(
    f"{DOMAIN}.backup_agent_listeners"
)


type GoogleDriveConfigEntry = ConfigEntry[DriveClient]


async def async_setup_entry(menuai: menuai, entry: GoogleDriveConfigEntry) -> bool:
    """Set up Google Drive from a config entry."""
    auth = AsyncConfigEntryAuth(
        async_get_clientsession(menuai),
        OAuth2Session(
            menuai, entry, await async_get_config_entry_implementation(menuai, entry)
        ),
    )

    # Test we can refresh the token and raise ConfigEntryAuthFailed or ConfigEntryNotReady if not
    await auth.async_get_access_token()

    client = DriveClient(await instance_id.async_get(menuai), auth)
    entry.runtime_data = client

    # Test we can access Google Drive and raise if not
    try:
        await client.async_create_ha_root_folder_if_not_exists()
    except GoogleDriveApiError as err:
        raise ConfigEntryNotReady from err

    def async_notify_backup_listeners() -> None:
        for listener in menuai.data.get(DATA_BACKUP_AGENT_LISTENERS, []):
            listener()

    entry.async_on_unload(entry.async_on_state_change(async_notify_backup_listeners))

    return True


async def async_unload_entry(
    menuai: menuai, entry: GoogleDriveConfigEntry
) -> bool:
    """Unload a config entry."""
    return True
