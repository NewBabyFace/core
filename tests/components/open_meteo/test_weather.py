"""Test for the open meteo weather entity."""

from unittest.mock import AsyncMock

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.weather import (
    DOMAIN as WEATHER_DOMAIN,
    SERVICE_GET_FORECASTS,
)
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai

from tests.common import MockConfigEntry


@pytest.mark.freeze_time("2021-11-24T03:00:00+00:00")
async def test_forecast_service(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_open_meteo: AsyncMock,
    snapshot: SnapshotAssertion,
) -> None:
    """Test forecast service."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    response = await menuai.services.async_call(
        WEATHER_DOMAIN,
        SERVICE_GET_FORECASTS,
        {ATTR_ENTITY_ID: "weather.home", "type": "daily"},
        blocking=True,
        return_response=True,
    )
    assert response == snapshot(name="forecast_daily")

    response = await menuai.services.async_call(
        WEATHER_DOMAIN,
        SERVICE_GET_FORECASTS,
        {ATTR_ENTITY_ID: "weather.home", "type": "hourly"},
        blocking=True,
        return_response=True,
    )
    assert response == snapshot(name="forecast_hourly")
