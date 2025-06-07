"""Fixtures for TechnoVE integration tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from technove import Station as TechnoVEStation

from menuai.components.technove.const import DOMAIN
from menuai.const import CONF_HOST
from menuai.core import menuai

from tests.common import MockConfigEntry, load_json_object_fixture


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return the default mocked config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.123"},
        unique_id="AA:AA:AA:AA:AA:BB",
    )


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Mock setting up a config entry."""
    with patch(
        "menuai.components.technove.async_setup_entry", return_value=True
    ) as mock_setup:
        yield mock_setup


@pytest.fixture
def mock_onboarding() -> Generator[MagicMock]:
    """Mock that MenuAI is currently onboarding."""
    with patch(
        "menuai.components.onboarding.async_is_onboarded",
        return_value=False,
    ) as mock_onboarding:
        yield mock_onboarding


@pytest.fixture
def device_fixture() -> TechnoVEStation:
    """Return the device fixture for a specific device."""
    return TechnoVEStation(load_json_object_fixture("station_charging.json", DOMAIN))


@pytest.fixture
def mock_technove(device_fixture: TechnoVEStation) -> Generator[MagicMock]:
    """Return a mocked TechnoVE client."""
    with (
        patch(
            "menuai.components.technove.coordinator.TechnoVE", autospec=True
        ) as technove_mock,
        patch(
            "menuai.components.technove.config_flow.TechnoVE", new=technove_mock
        ),
    ):
        technove = technove_mock.return_value
        technove.update.return_value = device_fixture
        technove.ip_address = "127.0.0.1"
        yield technove


@pytest.fixture
async def init_integration(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_technove: MagicMock,
) -> MockConfigEntry:
    """Set up the TechnoVE integration for testing."""
    mock_config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    return mock_config_entry
