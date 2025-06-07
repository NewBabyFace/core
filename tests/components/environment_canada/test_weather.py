"""Test weather."""

import copy
from typing import Any

from syrupy.assertion import SnapshotAssertion

from menuai.components.environment_canada.const import (
    DOMAIN,
    SERVICE_ENVIRONMENT_CANADA_FORECASTS,
)
from menuai.components.weather import (
    DOMAIN as WEATHER_DOMAIN,
    SERVICE_GET_FORECASTS,
)
from menuai.core import menuai

from . import init_integration


async def test_forecast_daily(
    menuai: menuai, snapshot: SnapshotAssertion, ec_data: dict[str, Any]
) -> None:
    """Test basic forecast."""

    # First entry in test data is a half day; we don't want that for this test
    local_ec_data = copy.deepcopy(ec_data)
    del local_ec_data["daily_forecasts"][0]

    await init_integration(menuai, local_ec_data)

    response = await menuai.services.async_call(
        WEATHER_DOMAIN,
        SERVICE_GET_FORECASTS,
        {
            "entity_id": "weather.home_forecast",
            "type": "daily",
        },
        blocking=True,
        return_response=True,
    )
    assert response == snapshot


async def test_forecast_daily_with_some_previous_days_data(
    menuai: menuai, snapshot: SnapshotAssertion, ec_data: dict[str, Any]
) -> None:
    """Test forecast with half day at start."""

    await init_integration(menuai, ec_data)

    response = await menuai.services.async_call(
        WEATHER_DOMAIN,
        SERVICE_GET_FORECASTS,
        {
            "entity_id": "weather.home_forecast",
            "type": "daily",
        },
        blocking=True,
        return_response=True,
    )
    assert response == snapshot


async def test_get_environment_canada_raw_forecast_data(
    menuai: menuai, snapshot: SnapshotAssertion, ec_data: dict[str, Any]
) -> None:
    """Test forecast with half day at start."""

    await init_integration(menuai, ec_data)

    response = await menuai.services.async_call(
        DOMAIN,
        SERVICE_ENVIRONMENT_CANADA_FORECASTS,
        {
            "entity_id": "weather.home_forecast",
        },
        blocking=True,
        return_response=True,
    )
    assert response == snapshot
