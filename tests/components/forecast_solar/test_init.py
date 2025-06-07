"""Tests for the Forecast.Solar integration."""

from unittest.mock import MagicMock, patch

from forecast_solar import ForecastSolarConnectionError
from syrupy.assertion import SnapshotAssertion

from menuai.components.forecast_solar.const import (
    CONF_AZIMUTH,
    CONF_DAMPING,
    CONF_DECLINATION,
    CONF_INVERTER_SIZE,
    DOMAIN,
)
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry


async def test_load_unload_config_entry(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_forecast_solar: MagicMock,
) -> None:
    """Test the Forecast.Solar configuration entry loading/unloading."""
    mock_config_entry.add_to_menuai(menuai)
    await async_setup_component(menuai, "forecast_solar", {})

    assert mock_config_entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert not menuai.data.get(DOMAIN)


@patch(
    "menuai.components.forecast_solar.coordinator.ForecastSolar.estimate",
    side_effect=ForecastSolarConnectionError,
)
async def test_config_entry_not_ready(
    mock_request: MagicMock,
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the Forecast.Solar configuration entry not ready."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_request.call_count == 1
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_migration(menuai: menuai, snapshot: SnapshotAssertion) -> None:
    """Test config entry version 1 -> 2 migration."""
    mock_config_entry = MockConfigEntry(
        title="Green House",
        unique_id="unique",
        domain=DOMAIN,
        data={
            CONF_LATITUDE: 52.42,
            CONF_LONGITUDE: 4.42,
        },
        options={
            CONF_API_KEY: "abcdef12345",
            CONF_DECLINATION: 30,
            CONF_AZIMUTH: 190,
            "modules power": 5100,
            CONF_DAMPING: 0.5,
            CONF_INVERTER_SIZE: 2000,
        },
    )
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert menuai.config_entries.async_get_entry(mock_config_entry.entry_id) == snapshot
