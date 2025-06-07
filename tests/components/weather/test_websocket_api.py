"""Test the weather websocket API."""

from menuai.components.weather import Forecast, WeatherEntityFeature
from menuai.components.weather.const import DOMAIN
from menuai.const import UnitOfTemperature
from menuai.core import menuai
from menuai.setup import async_setup_component

from . import MockWeatherTest, create_entity

from tests.typing import WebSocketGenerator


async def test_device_class_units(
    menuai: menuai, menuai_ws_client: WebSocketGenerator
) -> None:
    """Test we can get supported units."""
    assert await async_setup_component(menuai, DOMAIN, {})

    client = await menuai_ws_client(menuai)

    await client.send_json(
        {
            "id": 1,
            "type": "weather/convertible_units",
        }
    )
    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"] == {
        "units": {
            "precipitation_unit": ["in", "mm"],
            "pressure_unit": ["hPa", "inHg", "mbar", "mmHg"],
            "temperature_unit": ["°C", "°F"],
            "visibility_unit": ["km", "mi"],
            "wind_speed_unit": ["ft/s", "km/h", "kn", "m/s", "mph"],
        }
    }


async def test_subscribe_forecast(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    config_flow_fixture: None,
) -> None:
    """Test multiple forecast."""

    class MockWeatherMockForecast(MockWeatherTest):
        """Mock weather class."""

        async def async_forecast_daily(self) -> list[Forecast] | None:
            """Return the forecast_daily."""
            return self.forecast_list

    kwargs = {
        "native_temperature": 38,
        "native_temperature_unit": UnitOfTemperature.CELSIUS,
        "supported_features": WeatherEntityFeature.FORECAST_DAILY,
    }
    weather_entity = await create_entity(menuai, MockWeatherMockForecast, None, **kwargs)

    client = await menuai_ws_client(menuai)

    await client.send_json_auto_id(
        {
            "type": "weather/subscribe_forecast",
            "forecast_type": "daily",
            "entity_id": weather_entity.entity_id,
        }
    )
    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"] is None
    subscription_id = msg["id"]

    msg = await client.receive_json()
    assert msg["id"] == subscription_id
    assert msg["type"] == "event"
    forecast = msg["event"]
    assert forecast == {
        "type": "daily",
        "forecast": [
            {
                "cloud_coverage": None,
                "temperature": 38.0,
                "templow": 38.0,
                "uv_index": None,
                "wind_bearing": None,
            }
        ],
    }

    await weather_entity.async_update_listeners(None)
    msg = await client.receive_json()
    assert msg["event"] == forecast

    await weather_entity.async_update_listeners(["daily"])
    msg = await client.receive_json()
    assert msg["event"] == forecast

    weather_entity.forecast_list = None
    await weather_entity.async_update_listeners(None)
    msg = await client.receive_json()
    assert msg["event"] == {"type": "daily", "forecast": None}


async def test_subscribe_forecast_unknown_entity(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
) -> None:
    """Test multiple forecast."""

    assert await async_setup_component(menuai, DOMAIN, {})

    client = await menuai_ws_client(menuai)

    await client.send_json_auto_id(
        {
            "type": "weather/subscribe_forecast",
            "forecast_type": "daily",
            "entity_id": "weather.unknown",
        }
    )
    msg = await client.receive_json()
    assert not msg["success"]
    assert msg["error"] == {
        "code": "invalid_entity_id",
        "message": "Weather entity not found: weather.unknown",
    }


async def test_subscribe_forecast_unsupported(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    config_flow_fixture: None,
) -> None:
    """Test multiple forecast."""

    class MockWeatherMock(MockWeatherTest):
        """Mock weather class."""

    kwargs = {
        "native_temperature": 38,
        "native_temperature_unit": UnitOfTemperature.CELSIUS,
    }
    weather_entity = await create_entity(menuai, MockWeatherMock, None, **kwargs)
    client = await menuai_ws_client(menuai)

    await client.send_json_auto_id(
        {
            "type": "weather/subscribe_forecast",
            "forecast_type": "daily",
            "entity_id": weather_entity.entity_id,
        }
    )
    msg = await client.receive_json()
    assert not msg["success"]
    assert msg["error"] == {
        "code": "forecast_not_supported",
        "message": "The weather entity does not support forecast type: daily",
    }
