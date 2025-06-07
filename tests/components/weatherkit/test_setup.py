"""Test the WeatherKit setup process."""

from unittest.mock import patch

from apple_weatherkit.client import (
    WeatherKitApiClientAuthenticationError,
    WeatherKitApiClientError,
)

from menuai.components.weatherkit.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import EXAMPLE_CONFIG_DATA

from tests.common import MockConfigEntry


async def test_auth_error_handling(menuai: menuai) -> None:
    """Test that we handle authentication errors at setup properly."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        unique_id="0123456",
        data=EXAMPLE_CONFIG_DATA,
    )

    with (
        patch(
            "menuai.components.weatherkit.WeatherKitApiClient.get_weather_data",
            side_effect=WeatherKitApiClientAuthenticationError,
        ),
        patch(
            "menuai.components.weatherkit.WeatherKitApiClient.get_availability",
            side_effect=WeatherKitApiClientAuthenticationError,
        ),
    ):
        entry.add_to_menuai(menuai)
        setup_result = await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    assert setup_result is False


async def test_client_error_handling(menuai: menuai) -> None:
    """Test that we handle API client errors at setup properly."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        unique_id="0123456",
        data=EXAMPLE_CONFIG_DATA,
    )

    with (
        patch(
            "menuai.components.weatherkit.WeatherKitApiClient.get_weather_data",
            side_effect=WeatherKitApiClientError,
        ),
        patch(
            "menuai.components.weatherkit.WeatherKitApiClient.get_availability",
            side_effect=WeatherKitApiClientError,
        ),
    ):
        entry.add_to_menuai(menuai)
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY
