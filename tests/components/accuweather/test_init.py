"""Test init of AccuWeather integration."""

from unittest.mock import AsyncMock

from accuweather import ApiError
from freezegun.api import FrozenDateTimeFactory

from menuai.components.accuweather.const import (
    DOMAIN,
    UPDATE_INTERVAL_DAILY_FORECAST,
    UPDATE_INTERVAL_OBSERVATION,
)
from menuai.components.sensor import DOMAIN as SENSOR_DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import init_integration

from tests.common import MockConfigEntry, async_fire_time_changed


async def test_async_setup_entry(
    menuai: menuai, mock_accuweather_client: AsyncMock
) -> None:
    """Test a successful setup entry."""
    await init_integration(menuai)

    state = menuai.states.get("weather.home")
    assert state is not None
    assert state.state != STATE_UNAVAILABLE
    assert state.state == "sunny"


async def test_config_not_ready(
    menuai: menuai, mock_accuweather_client: AsyncMock
) -> None:
    """Test for setup failure if connection to AccuWeather is missing."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        unique_id="0123456",
        data={
            "api_key": "32-character-string-1234567890qw",
            "latitude": 55.55,
            "longitude": 122.12,
            "name": "Home",
        },
    )

    mock_accuweather_client.async_get_current_conditions.side_effect = ApiError(
        "API Error"
    )

    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload_entry(
    menuai: menuai, mock_accuweather_client: AsyncMock
) -> None:
    """Test successful unload of entry."""
    entry = await init_integration(menuai)

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert not menuai.data.get(DOMAIN)


async def test_update_interval(
    menuai: menuai,
    mock_accuweather_client: AsyncMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test correct update interval."""
    entry = await init_integration(menuai)

    assert entry.state is ConfigEntryState.LOADED

    assert mock_accuweather_client.async_get_current_conditions.call_count == 1
    assert mock_accuweather_client.async_get_daily_forecast.call_count == 1

    freezer.tick(UPDATE_INTERVAL_OBSERVATION)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert mock_accuweather_client.async_get_current_conditions.call_count == 2

    freezer.tick(UPDATE_INTERVAL_DAILY_FORECAST)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert mock_accuweather_client.async_get_daily_forecast.call_count == 2


async def test_remove_ozone_sensors(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_accuweather_client: AsyncMock,
) -> None:
    """Test remove ozone sensors from registry."""
    entity_registry.async_get_or_create(
        SENSOR_DOMAIN,
        DOMAIN,
        "0123456-ozone-0",
        suggested_object_id="home_ozone_0d",
        disabled_by=None,
    )

    await init_integration(menuai)

    entry = entity_registry.async_get("sensor.home_ozone_0d")
    assert entry is None
