"""Test WeatherKit data coordinator."""

from datetime import timedelta
from unittest.mock import patch

from apple_weatherkit.client import WeatherKitApiClientError
from freezegun.api import FrozenDateTimeFactory

from menuai.const import STATE_UNAVAILABLE
from menuai.core import menuai

from . import init_integration, mock_weather_response

from tests.common import async_fire_time_changed


async def test_update_uses_stale_data_before_threshold(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that stale data from the last successful update is used if an update failure occurs before the threshold."""
    with mock_weather_response():
        await init_integration(menuai)

    state = menuai.states.get("weather.home")
    assert state
    assert state.state != STATE_UNAVAILABLE

    initial_state = state.state

    # Expect stale data to be used before one hour

    with patch(
        "menuai.components.weatherkit.WeatherKitApiClient.get_weather_data",
        side_effect=WeatherKitApiClientError,
    ):
        freezer.tick(timedelta(minutes=59))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()

    state = menuai.states.get("weather.home")
    assert state
    assert state.state == initial_state


async def test_update_becomes_unavailable_after_threshold(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that the entity becomes unavailable if an update failure occurs after the threshold."""
    with mock_weather_response():
        await init_integration(menuai)

    # Expect state to be unavailable after one hour

    with patch(
        "menuai.components.weatherkit.WeatherKitApiClient.get_weather_data",
        side_effect=WeatherKitApiClientError,
    ):
        freezer.tick(timedelta(hours=1, minutes=5))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()

    state = menuai.states.get("weather.home")
    assert state
    assert state.state == STATE_UNAVAILABLE


async def test_update_recovers_after_failure(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that a successful update after repeated failures recovers the entity's state."""
    with mock_weather_response():
        await init_integration(menuai)

    # Trigger a failure after threshold

    with patch(
        "menuai.components.weatherkit.WeatherKitApiClient.get_weather_data",
        side_effect=WeatherKitApiClientError,
    ):
        freezer.tick(timedelta(hours=1, minutes=5))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()

    # Expect that a successful update recovers the entity

    with mock_weather_response():
        freezer.tick(timedelta(minutes=5))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()

    state = menuai.states.get("weather.home")
    assert state
    assert state.state != STATE_UNAVAILABLE
