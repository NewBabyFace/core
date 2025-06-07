"""The Flick Electric integration."""

from datetime import datetime as dt
import logging
from typing import Any

import jwt
from pyflick import FlickAPI
from pyflick.authentication import SimpleFlickAuth
from pyflick.const import DEFAULT_CLIENT_ID, DEFAULT_CLIENT_SECRET

from menuai.const import (
    CONF_ACCESS_TOKEN,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_PASSWORD,
    CONF_USERNAME,
    Platform,
)
from menuai.core import menuai
from menuai.helpers import aiohttp_client

from .const import CONF_ACCOUNT_ID, CONF_SUPPLY_NODE_REF, CONF_TOKEN_EXPIRY
from .coordinator import FlickConfigEntry, FlickElectricDataCoordinator

_LOGGER = logging.getLogger(__name__)

CONF_ID_TOKEN = "id_token"

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: FlickConfigEntry) -> bool:
    """Set up Flick Electric from a config entry."""
    auth = menuaiFlickAuth(menuai, entry)

    coordinator = FlickElectricDataCoordinator(menuai, entry, FlickAPI(auth))

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: FlickConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(
    menuai: menuai, config_entry: FlickConfigEntry
) -> bool:
    """Migrate old entry."""
    _LOGGER.debug(
        "Migrating configuration from version %s.%s",
        config_entry.version,
        config_entry.minor_version,
    )

    if config_entry.version > 2:
        return False

    if config_entry.version == 1:
        api = FlickAPI(menuaiFlickAuth(menuai, config_entry))

        accounts = await api.getCustomerAccounts()
        active_accounts = [
            account for account in accounts if account["status"] == "active"
        ]

        # A single active account can be auto-migrated
        if (len(active_accounts)) == 1:
            account = active_accounts[0]

            new_data = {**config_entry.data}
            new_data[CONF_ACCOUNT_ID] = account["id"]
            new_data[CONF_SUPPLY_NODE_REF] = account["main_consumer"]["supply_node_ref"]
            menuai.config_entries.async_update_entry(
                config_entry,
                title=account["address"],
                unique_id=account["id"],
                data=new_data,
                version=2,
            )
            return True

        config_entry.async_start_reauth(menuai, data={**config_entry.data})
        return False

    return True


class menuaiFlickAuth(SimpleFlickAuth):
    """Implementation of AbstractFlickAuth based on a MenuAI entity config."""

    def __init__(self, menuai: menuai, entry: FlickConfigEntry) -> None:
        """Flick authentication based on a MenuAI entity config."""
        super().__init__(
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            client_id=entry.data.get(CONF_CLIENT_ID, DEFAULT_CLIENT_ID),
            client_secret=entry.data.get(CONF_CLIENT_SECRET, DEFAULT_CLIENT_SECRET),
            websession=aiohttp_client.async_get_clientsession(menuai),
        )
        self._entry = entry
        self._menuai = menuai

    async def _get_entry_token(self) -> dict[str, Any]:
        # No token saved, generate one
        if (
            CONF_TOKEN_EXPIRY not in self._entry.data
            or CONF_ACCESS_TOKEN not in self._entry.data
        ):
            await self._update_token()

        # Token is expired, generate a new one
        if self._entry.data[CONF_TOKEN_EXPIRY] <= dt.now().timestamp():
            await self._update_token()

        return self._entry.data[CONF_ACCESS_TOKEN]

    async def _update_token(self):
        _LOGGER.debug("Fetching new access token")

        token = await super().get_new_token(
            self._username, self._password, self._client_id, self._client_secret
        )

        _LOGGER.debug("New token: %s", token)

        # Flick will send the same token, but expiry is relative - so grab it from the token
        token_decoded = jwt.decode(
            token[CONF_ID_TOKEN], options={"verify_signature": False}
        )

        self._menuai.config_entries.async_update_entry(
            self._entry,
            data={
                **self._entry.data,
                CONF_ACCESS_TOKEN: token,
                CONF_TOKEN_EXPIRY: token_decoded["exp"],
            },
        )

    async def async_get_access_token(self):
        """Get Access Token from menuai Storage."""
        token = await self._get_entry_token()

        return token[CONF_ID_TOKEN]
