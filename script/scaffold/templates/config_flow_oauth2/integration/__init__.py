"""The NEW_NAME integration."""

from __future__ import annotations

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import aiohttp_client, config_entry_oauth2_flow

from . import api

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
_PLATFORMS: list[Platform] = [Platform.LIGHT]

# TODO Create ConfigEntry type alias with ConfigEntryAuth or AsyncConfigEntryAuth object
# TODO Rename type alias and update all entry annotations
type New_NameConfigEntry = ConfigEntry[api.AsyncConfigEntryAuth]


# # TODO Update entry annotation
async def async_setup_entry(menuai: menuai, entry: New_NameConfigEntry) -> bool:
    """Set up NEW_NAME from a config entry."""
    implementation = (
        await config_entry_oauth2_flow.async_get_config_entry_implementation(
            menuai, entry
        )
    )

    session = config_entry_oauth2_flow.OAuth2Session(menuai, entry, implementation)

    # If using a requests-based API lib
    entry.runtime_data = api.ConfigEntryAuth(menuai, session)

    # If using an aiohttp-based API lib
    entry.runtime_data = api.AsyncConfigEntryAuth(
        aiohttp_client.async_get_clientsession(menuai), session
    )

    await menuai.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True


# TODO Update entry annotation
async def async_unload_entry(menuai: menuai, entry: New_NameConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, _PLATFORMS)
