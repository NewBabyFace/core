"""Data UpdateCoordinator for the Remote Calendar integration."""

from datetime import timedelta
import logging

from httpx import HTTPError, InvalidURL
from ical.calendar import Calendar

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_URL
from menuai.core import menuai
from menuai.helpers.httpx_client import get_async_client
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .ics import InvalidIcsException, parse_calendar

type RemoteCalendarConfigEntry = ConfigEntry[RemoteCalendarDataUpdateCoordinator]

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(days=1)


class RemoteCalendarDataUpdateCoordinator(DataUpdateCoordinator[Calendar]):
    """Class to manage fetching calendar data."""

    config_entry: RemoteCalendarConfigEntry
    ics: str

    def __init__(
        self,
        menuai: menuai,
        config_entry: RemoteCalendarConfigEntry,
    ) -> None:
        """Initialize data updater."""
        super().__init__(
            menuai,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
            always_update=True,
        )
        self._client = get_async_client(menuai)
        self._url = config_entry.data[CONF_URL]

    async def _async_update_data(self) -> Calendar:
        """Update data from the url."""
        try:
            res = await self._client.get(self._url, follow_redirects=True)
            res.raise_for_status()
        except (HTTPError, InvalidURL) as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="unable_to_fetch",
                translation_placeholders={"err": str(err)},
            ) from err
        try:
            self.ics = res.text
            return await parse_calendar(self.menuai, res.text)
        except InvalidIcsException as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="unable_to_parse",
                translation_placeholders={"err": str(err)},
            ) from err
