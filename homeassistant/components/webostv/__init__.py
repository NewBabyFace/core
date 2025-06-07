"""The LG webOS TV integration."""

from __future__ import annotations

from contextlib import suppress

from aiowebostv import WebOsClient, WebOsTvPairError

from menuai.components import notify as menuai_notify
from menuai.const import (
    CONF_CLIENT_SECRET,
    CONF_HOST,
    CONF_NAME,
    EVENT_menuai_STOP,
    Platform,
)
from menuai.core import Event, menuai
from menuai.exceptions import ConfigEntryAuthFailed
from menuai.helpers import config_validation as cv, discovery
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.typing import ConfigType

from .const import (
    ATTR_CONFIG_ENTRY_ID,
    DATA_menuai_CONFIG,
    DOMAIN,
    PLATFORMS,
    WEBOSTV_EXCEPTIONS,
)
from .helpers import WebOsTvConfigEntry, update_client_key

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the LG webOS TV platform."""
    menuai.data.setdefault(DOMAIN, {DATA_menuai_CONFIG: config})

    return True


async def async_setup_entry(menuai: menuai, entry: WebOsTvConfigEntry) -> bool:
    """Set the config entry up."""
    host = entry.data[CONF_HOST]
    key = entry.data[CONF_CLIENT_SECRET]

    # Attempt a connection, but fail gracefully if tv is off for example.
    entry.runtime_data = client = WebOsClient(
        host, key, client_session=async_get_clientsession(menuai)
    )
    with suppress(*WEBOSTV_EXCEPTIONS):
        try:
            await client.connect()
        except WebOsTvPairError as err:
            raise ConfigEntryAuthFailed(err) from err

    # If pairing request accepted there will be no error
    # Update the stored key without triggering reauth
    update_client_key(menuai, entry)

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # set up notify platform, no entry support for notify component yet,
    # have to use discovery to load platform.
    menuai.async_create_task(
        discovery.async_load_platform(
            menuai,
            Platform.NOTIFY,
            DOMAIN,
            {
                CONF_NAME: entry.title,
                ATTR_CONFIG_ENTRY_ID: entry.entry_id,
            },
            menuai.data[DOMAIN][DATA_menuai_CONFIG],
        )
    )

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    async def async_on_stop(_event: Event) -> None:
        """Unregister callbacks and disconnect."""
        client.clear_state_update_callbacks()
        await client.disconnect()

    entry.async_on_unload(
        menuai.bus.async_listen_once(EVENT_menuai_STOP, async_on_stop)
    )
    return True


async def async_update_options(menuai: menuai, entry: WebOsTvConfigEntry) -> None:
    """Update options."""
    await menuai.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(menuai: menuai, entry: WebOsTvConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        client = entry.runtime_data
        await menuai_notify.async_reload(menuai, DOMAIN)
        client.clear_state_update_callbacks()
        await client.disconnect()

    return unload_ok
