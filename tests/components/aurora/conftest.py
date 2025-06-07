"""Common fixtures for the Aurora tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from menuai.components.aurora.const import CONF_THRESHOLD, DOMAIN
from menuai.const import CONF_LATITUDE, CONF_LONGITUDE

from tests.common import MockConfigEntry


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "menuai.components.aurora.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture
def mock_aurora_client() -> Generator[AsyncMock]:
    """Mock a menuai Analytics client."""
    with (
        patch(
            "menuai.components.aurora.coordinator.AuroraForecast",
            autospec=True,
        ) as mock_client,
        patch(
            "menuai.components.aurora.config_flow.AuroraForecast",
            new=mock_client,
        ),
    ):
        client = mock_client.return_value
        client.get_forecast_data.return_value = 42
        yield client


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Mock a config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Aurora visibility",
        data={
            CONF_LATITUDE: -10,
            CONF_LONGITUDE: 10.2,
        },
        options={
            CONF_THRESHOLD: 75,
        },
    )
