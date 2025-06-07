"""The Twitch component."""

from __future__ import annotations

from typing import cast

from aiohttp.client_exceptions import ClientError, ClientResponseError
from twitchAPI.twitch import Twitch

from menuai.const import CONF_ACCESS_TOKEN, CONF_TOKEN
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from menuai.helpers.config_entry_oauth2_flow import (
    LocalOAuth2Implementation,
    OAuth2Session,
    async_get_config_entry_implementation,
)

from .const import OAUTH_SCOPES, PLATFORMS
from .coordinator import TwitchConfigEntry, TwitchCoordinator


async def async_setup_entry(menuai: menuai, entry: TwitchConfigEntry) -> bool:
    """Set up Twitch from a config entry."""
    implementation = cast(
        LocalOAuth2Implementation,
        await async_get_config_entry_implementation(menuai, entry),
    )
    session = OAuth2Session(menuai, entry, implementation)
    try:
        await session.async_ensure_token_valid()
    except ClientResponseError as err:
        if 400 <= err.status < 500:
            raise ConfigEntryAuthFailed(
                "OAuth session is not valid, reauth required"
            ) from err
        raise ConfigEntryNotReady from err
    except ClientError as err:
        raise ConfigEntryNotReady from err

    access_token = entry.data[CONF_TOKEN][CONF_ACCESS_TOKEN]
    client = Twitch(
        app_id=implementation.client_id,
        authenticate_app=False,
    )
    client.auto_refresh_auth = False
    await client.set_user_authentication(access_token, scope=OAUTH_SCOPES)

    coordinator = TwitchCoordinator(menuai, client, session, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: TwitchConfigEntry) -> bool:
    """Unload Twitch config entry."""

    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
