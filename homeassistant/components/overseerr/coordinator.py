"""Define an object to coordinate fetching Overseerr data."""

from datetime import timedelta

from python_overseerr import (
    OverseerrAuthenticationError,
    OverseerrClient,
    OverseerrConnectionError,
    RequestCount,
)
from yarl import URL

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_API_KEY, CONF_HOST, CONF_PORT, CONF_SSL
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER

type OverseerrConfigEntry = ConfigEntry[OverseerrCoordinator]


class OverseerrCoordinator(DataUpdateCoordinator[RequestCount]):
    """Class to manage fetching Overseerr data."""

    config_entry: OverseerrConfigEntry

    def __init__(self, menuai: menuai, entry: OverseerrConfigEntry) -> None:
        """Initialize."""
        super().__init__(
            menuai,
            LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(minutes=5),
        )
        host = entry.data[CONF_HOST]
        port = entry.data[CONF_PORT]
        ssl = entry.data[CONF_SSL]
        self.client = OverseerrClient(
            host,
            port,
            entry.data[CONF_API_KEY],
            ssl=ssl,
            session=async_get_clientsession(menuai),
        )
        self.url = URL.build(host=host, port=port, scheme="https" if ssl else "http")
        self.push = False

    async def _async_update_data(self) -> RequestCount:
        """Fetch data from API endpoint."""
        try:
            return await self.client.get_request_count()
        except OverseerrAuthenticationError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="auth_error",
            ) from err
        except OverseerrConnectionError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="connection_error",
                translation_placeholders={"error": str(err)},
            ) from err
