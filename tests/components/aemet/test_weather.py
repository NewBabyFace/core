"""The sensor tests for the AEMET OpenData platform."""

import datetime
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.aemet.const import ATTRIBUTION
from menuai.components.aemet.coordinator import WEATHER_UPDATE_INTERVAL
from menuai.components.weather import (
    ATTR_CONDITION_SNOWY,
    ATTR_WEATHER_HUMIDITY,
    ATTR_WEATHER_PRESSURE,
    ATTR_WEATHER_TEMPERATURE,
    ATTR_WEATHER_WIND_BEARING,
    ATTR_WEATHER_WIND_GUST_SPEED,
    ATTR_WEATHER_WIND_SPEED,
    DOMAIN as WEATHER_DOMAIN,
    SERVICE_GET_FORECASTS,
)
from menuai.const import ATTR_ATTRIBUTION
from menuai.core import menuai

from .util import async_init_integration, mock_api_call

from tests.typing import WebSocketGenerator


async def test_aemet_weather(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test states of the weather."""

    await menuai.config.async_set_time_zone("UTC")
    freezer.move_to("2021-01-09 12:00:00+00:00")
    await async_init_integration(menuai)

    state = menuai.states.get("weather.aemet")
    assert state
    assert state.state == ATTR_CONDITION_SNOWY
    assert state.attributes[ATTR_ATTRIBUTION] == ATTRIBUTION
    assert state.attributes[ATTR_WEATHER_HUMIDITY] == 99.0
    assert state.attributes[ATTR_WEATHER_PRESSURE] == 1004.4  # 100440.0 Pa -> hPa
    assert state.attributes[ATTR_WEATHER_TEMPERATURE] == -0.7
    assert state.attributes[ATTR_WEATHER_WIND_BEARING] == 122.0
    assert state.attributes[ATTR_WEATHER_WIND_GUST_SPEED] == 12.2
    assert state.attributes[ATTR_WEATHER_WIND_SPEED] == 3.2

    state = menuai.states.get("weather.aemet_hourly")
    assert state is None


@pytest.mark.parametrize(
    ("service"),
    [SERVICE_GET_FORECASTS],
)
async def test_forecast_service(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    snapshot: SnapshotAssertion,
    service: str,
) -> None:
    """Test multiple forecast."""

    await menuai.config.async_set_time_zone("UTC")
    freezer.move_to("2021-01-09 12:00:00+00:00")
    await async_init_integration(menuai)

    response = await menuai.services.async_call(
        WEATHER_DOMAIN,
        service,
        {
            "entity_id": "weather.aemet",
            "type": "daily",
        },
        blocking=True,
        return_response=True,
    )
    assert response == snapshot

    response = await menuai.services.async_call(
        WEATHER_DOMAIN,
        service,
        {
            "entity_id": "weather.aemet",
            "type": "hourly",
        },
        blocking=True,
        return_response=True,
    )
    assert response == snapshot


@pytest.mark.parametrize("forecast_type", ["daily", "hourly"])
async def test_forecast_subscription(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    freezer: FrozenDateTimeFactory,
    snapshot: SnapshotAssertion,
    forecast_type: str,
) -> None:
    """Test multiple forecast."""
    client = await menuai_ws_client(menuai)

    await menuai.config.async_set_time_zone("UTC")
    freezer.move_to("2021-01-09 12:00:00+00:00")
    await async_init_integration(menuai)

    await client.send_json_auto_id(
        {
            "type": "weather/subscribe_forecast",
            "forecast_type": forecast_type,
            "entity_id": "weather.aemet",
        }
    )
    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"] is None
    subscription_id = msg["id"]

    msg = await client.receive_json()
    assert msg["id"] == subscription_id
    assert msg["type"] == "event"
    forecast1 = msg["event"]["forecast"]

    assert forecast1 == snapshot

    with patch(
        "menuai.components.aemet.AEMET.api_call",
        side_effect=mock_api_call,
    ):
        freezer.tick(WEATHER_UPDATE_INTERVAL + datetime.timedelta(seconds=1))
        await menuai.async_block_till_done()
        msg = await client.receive_json()

    assert msg["id"] == subscription_id
    assert msg["type"] == "event"
    forecast2 = msg["event"]["forecast"]

    assert forecast2 == snapshot
