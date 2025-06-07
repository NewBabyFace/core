"""Test forecast solar energy platform."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from menuai.components.forecast_solar import energy
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from tests.common import MockConfigEntry


async def test_energy_solar_forecast(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_forecast_solar: MagicMock,
) -> None:
    """Test the Forecast.Solar energy platform solar forecast."""
    mock_forecast_solar.estimate.return_value.wh_period = {
        datetime(2021, 6, 27, 13, 0, tzinfo=UTC): 12,
        datetime(2021, 6, 27, 14, 0, tzinfo=UTC): 8,
    }

    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED

    assert await energy.async_get_solar_forecast(menuai, mock_config_entry.entry_id) == {
        "wh_hours": {
            "2021-06-27T13:00:00+00:00": 12,
            "2021-06-27T14:00:00+00:00": 8,
        }
    }
