"""Sensor entity tests for the WeatherKit integration."""

from typing import Any

import pytest

from menuai.core import menuai

from . import init_integration, mock_weather_response


@pytest.mark.parametrize(
    ("entity_name", "expected_value"),
    [
        ("sensor.home_precipitation_intensity", 0.7),
        ("sensor.home_pressure_trend", "rising"),
    ],
)
async def test_sensor_values(
    menuai: menuai, entity_name: str, expected_value: Any
) -> None:
    """Test that various sensor values match what we expect."""
    with mock_weather_response():
        await init_integration(menuai)

    state = menuai.states.get(entity_name)
    assert state
    assert state.state == str(expected_value)
