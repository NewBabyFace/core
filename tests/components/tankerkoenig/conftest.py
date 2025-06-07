"""Fixtures for Tankerkoenig integration tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from menuai.components.tankerkoenig import DOMAIN
from menuai.const import CONF_SHOW_ON_MAP
from menuai.core import menuai
from menuai.setup import async_setup_component

from .const import CONFIG_DATA, NEARBY_STATIONS, PRICES, STATION

from tests.common import MockConfigEntry


@pytest.fixture(name="tankerkoenig")
def mock_tankerkoenig() -> Generator[AsyncMock]:
    """Mock the aiotankerkoenig client."""
    with (
        patch(
            "menuai.components.tankerkoenig.coordinator.Tankerkoenig",
            autospec=True,
        ) as mock_tankerkoenig,
        patch(
            "menuai.components.tankerkoenig.config_flow.Tankerkoenig",
            new=mock_tankerkoenig,
        ),
    ):
        mock = mock_tankerkoenig.return_value
        mock.station_details.return_value = STATION
        mock.prices.return_value = PRICES
        mock.nearby_stations.return_value = NEARBY_STATIONS
        yield mock


@pytest.fixture(name="config_entry")
async def mock_config_entry(menuai: menuai) -> MockConfigEntry:
    """Return a MockConfigEntry for testing."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Mock Title",
        unique_id="51.0_13.0",
        entry_id="8036b4412f2fae6bb9dbab7fe8e37f87",
        options={
            CONF_SHOW_ON_MAP: True,
        },
        data=CONFIG_DATA,
    )


@pytest.fixture(name="setup_integration")
async def mock_setup_integration(
    menuai: menuai, config_entry: MockConfigEntry, tankerkoenig: AsyncMock
) -> None:
    """Fixture for setting up the component."""
    config_entry.add_to_menuai(menuai)

    assert await async_setup_component(menuai, DOMAIN, {})
    await menuai.async_block_till_done()
