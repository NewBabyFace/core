"""Provides the Geocaching DataUpdateCoordinator."""

from __future__ import annotations

from geocachingapi.exceptions import GeocachingApiError, GeocachingInvalidSettingsError
from geocachingapi.geocachingapi import GeocachingApi
from geocachingapi.models import GeocachingStatus

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.config_entry_oauth2_flow import OAuth2Session
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, ENVIRONMENT, LOGGER, UPDATE_INTERVAL

type GeocachingConfigEntry = ConfigEntry[GeocachingDataUpdateCoordinator]


class GeocachingDataUpdateCoordinator(DataUpdateCoordinator[GeocachingStatus]):
    """Class to manage fetching Geocaching data from single endpoint."""

    config_entry: GeocachingConfigEntry

    def __init__(
        self,
        menuai: menuai,
        *,
        entry: GeocachingConfigEntry,
        session: OAuth2Session,
    ) -> None:
        """Initialize global Geocaching data updater."""
        self.session = session

        async def async_token_refresh() -> str:
            await session.async_ensure_token_valid()
            token = session.token["access_token"]
            LOGGER.debug(str(token))
            return str(token)

        client_session = async_get_clientsession(menuai)

        self.geocaching = GeocachingApi(
            environment=ENVIRONMENT,
            token=session.token["access_token"],
            session=client_session,
            token_refresh_method=async_token_refresh,
        )

        super().__init__(
            menuai,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> GeocachingStatus:
        """Fetch the latest Geocaching status."""
        try:
            return await self.geocaching.update()
        except GeocachingInvalidSettingsError as error:
            raise UpdateFailed(f"Invalid integration configuration: {error}") from error
        except GeocachingApiError as error:
            raise UpdateFailed(f"Invalid response from API: {error}") from error
