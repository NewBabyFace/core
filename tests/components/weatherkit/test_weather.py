"""Weather entity tests for the WeatherKit integration."""

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.weather import (
    ATTR_WEATHER_APPARENT_TEMPERATURE,
    ATTR_WEATHER_CLOUD_COVERAGE,
    ATTR_WEATHER_DEW_POINT,
    ATTR_WEATHER_HUMIDITY,
    ATTR_WEATHER_PRESSURE,
    ATTR_WEATHER_TEMPERATURE,
    ATTR_WEATHER_UV_INDEX,
    ATTR_WEATHER_VISIBILITY,
    ATTR_WEATHER_WIND_BEARING,
    ATTR_WEATHER_WIND_GUST_SPEED,
    ATTR_WEATHER_WIND_SPEED,
    DOMAIN as WEATHER_DOMAIN,
    SERVICE_GET_FORECASTS,
    WeatherEntityFeature,
)
from menuai.components.weatherkit.const import ATTRIBUTION
from menuai.const import ATTR_ATTRIBUTION, ATTR_SUPPORTED_FEATURES
from menuai.core import menuai

from . import init_integration, mock_weather_response


async def test_current_weather(menuai: menuai) -> None:
    """Test states of the current weather."""
    with mock_weather_response():
        await init_integration(menuai)

    state = menuai.states.get("weather.home")
    assert state
    assert state.state == "partlycloudy"
    assert state.attributes[ATTR_WEATHER_HUMIDITY] == 91
    assert state.attributes[ATTR_WEATHER_PRESSURE] == 1009.8
    assert state.attributes[ATTR_WEATHER_TEMPERATURE] == 22.9
    assert state.attributes[ATTR_WEATHER_VISIBILITY] == 20.97
    assert state.attributes[ATTR_WEATHER_WIND_BEARING] == 259
    assert state.attributes[ATTR_WEATHER_WIND_SPEED] == 5.23
    assert state.attributes[ATTR_WEATHER_APPARENT_TEMPERATURE] == 24.9
    assert state.attributes[ATTR_WEATHER_DEW_POINT] == 21.3
    assert state.attributes[ATTR_WEATHER_CLOUD_COVERAGE] == 62
    assert state.attributes[ATTR_WEATHER_WIND_GUST_SPEED] == 10.53
    assert state.attributes[ATTR_WEATHER_UV_INDEX] == 1
    assert state.attributes[ATTR_ATTRIBUTION] == ATTRIBUTION


async def test_current_weather_nighttime(menuai: menuai) -> None:
    """Test that the condition is clear-night when it's sunny and night time."""
    with mock_weather_response(is_night_time=True):
        await init_integration(menuai)

    state = menuai.states.get("weather.home")
    assert state
    assert state.state == "clear-night"


async def test_daily_forecast_missing(menuai: menuai) -> None:
    """Test that daily forecast is not supported when WeatherKit doesn't support it."""
    with mock_weather_response(has_daily_forecast=False):
        await init_integration(menuai)

    state = menuai.states.get("weather.home")
    assert state
    assert (
        state.attributes[ATTR_SUPPORTED_FEATURES] & WeatherEntityFeature.FORECAST_DAILY
    ) == 0


async def test_hourly_forecast_missing(menuai: menuai) -> None:
    """Test that hourly forecast is not supported when WeatherKit doesn't support it."""
    with mock_weather_response(has_hourly_forecast=False):
        await init_integration(menuai)

    state = menuai.states.get("weather.home")
    assert state
    assert (
        state.attributes[ATTR_SUPPORTED_FEATURES] & WeatherEntityFeature.FORECAST_HOURLY
    ) == 0


@pytest.mark.parametrize(
    ("service"),
    [SERVICE_GET_FORECASTS],
)
async def test_hourly_forecast(
    menuai: menuai, snapshot: SnapshotAssertion, service: str
) -> None:
    """Test states of the hourly forecast."""
    with mock_weather_response():
        await init_integration(menuai)

    response = await menuai.services.async_call(
        WEATHER_DOMAIN,
        service,
        {
            "entity_id": "weather.home",
            "type": "hourly",
        },
        blocking=True,
        return_response=True,
    )
    assert response == snapshot


@pytest.mark.parametrize(
    ("service"),
    [SERVICE_GET_FORECASTS],
)
async def test_daily_forecast(
    menuai: menuai, snapshot: SnapshotAssertion, service: str
) -> None:
    """Test states of the daily forecast."""
    with mock_weather_response():
        await init_integration(menuai)

    response = await menuai.services.async_call(
        WEATHER_DOMAIN,
        service,
        {
            "entity_id": "weather.home",
            "type": "daily",
        },
        blocking=True,
        return_response=True,
    )
    assert response == snapshot
