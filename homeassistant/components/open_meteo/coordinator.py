"""DataUpdateCoordinator for the Open-Meteo integration."""

from __future__ import annotations

from open_meteo import (
    DailyParameters,
    Forecast,
    HourlyParameters,
    OpenMeteo,
    OpenMeteoError,
    PrecipitationUnit,
    TemperatureUnit,
    WindSpeedUnit,
)

from menuai.config_entries import ConfigEntry
from menuai.const import ATTR_LATITUDE, ATTR_LONGITUDE, CONF_ZONE
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER, SCAN_INTERVAL

type OpenMeteoConfigEntry = ConfigEntry[OpenMeteoDataUpdateCoordinator]


class OpenMeteoDataUpdateCoordinator(DataUpdateCoordinator[Forecast]):
    """A Open-Meteo Data Update Coordinator."""

    config_entry: OpenMeteoConfigEntry

    def __init__(self, menuai: menuai, config_entry: OpenMeteoConfigEntry) -> None:
        """Initialize the Open-Meteo coordinator."""
        super().__init__(
            menuai,
            LOGGER,
            config_entry=config_entry,
            name=f"{DOMAIN}_{config_entry.data[CONF_ZONE]}",
            update_interval=SCAN_INTERVAL,
        )
        session = async_get_clientsession(menuai)
        self.open_meteo = OpenMeteo(session=session)

    async def _async_update_data(self) -> Forecast:
        """Fetch data from Sensibo."""
        if (zone := self.menuai.states.get(self.config_entry.data[CONF_ZONE])) is None:
            raise UpdateFailed(f"Zone '{self.config_entry.data[CONF_ZONE]}' not found")

        try:
            return await self.open_meteo.forecast(
                latitude=zone.attributes[ATTR_LATITUDE],
                longitude=zone.attributes[ATTR_LONGITUDE],
                current_weather=True,
                daily=[
                    DailyParameters.PRECIPITATION_SUM,
                    DailyParameters.TEMPERATURE_2M_MAX,
                    DailyParameters.TEMPERATURE_2M_MIN,
                    DailyParameters.WEATHER_CODE,
                    DailyParameters.WIND_DIRECTION_10M_DOMINANT,
                    DailyParameters.WIND_SPEED_10M_MAX,
                ],
                hourly=[
                    HourlyParameters.PRECIPITATION,
                    HourlyParameters.TEMPERATURE_2M,
                    HourlyParameters.WEATHER_CODE,
                ],
                precipitation_unit=PrecipitationUnit.MILLIMETERS,
                temperature_unit=TemperatureUnit.CELSIUS,
                timezone="UTC",
                wind_speed_unit=WindSpeedUnit.KILOMETERS_PER_HOUR,
            )
        except OpenMeteoError as err:
            raise UpdateFailed("Open-Meteo API communication error") from err
