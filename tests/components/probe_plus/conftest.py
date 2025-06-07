"""Common fixtures for the Probe Plus tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

from pyprobeplus.parser import ParserBase, ProbePlusData
import pytest

from menuai.components.probe_plus.const import DOMAIN
from menuai.const import CONF_ADDRESS
from menuai.core import menuai

from tests.common import MockConfigEntry


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "menuai.components.probe_plus.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture
def mock_config_entry(menuai: menuai) -> MockConfigEntry:
    """Return the default mocked config entry."""
    return MockConfigEntry(
        title="FM210 aa:bb:cc:dd:ee:ff",
        domain=DOMAIN,
        version=1,
        data={
            CONF_ADDRESS: "aa:bb:cc:dd:ee:ff",
        },
        unique_id="aa:bb:cc:dd:ee:ff",
    )


@pytest.fixture
def mock_probe_plus() -> MagicMock:
    """Mock the Probe Plus device."""
    with patch(
        "menuai.components.probe_plus.coordinator.ProbePlusDevice",
        autospec=True,
    ) as mock_device:
        device = mock_device.return_value
        device.connected = True
        device.name = "FM210 aa:bb:cc:dd:ee:ff"
        mock_state = ParserBase()
        mock_state.state = ProbePlusData(
            relay_battery=50,
            probe_battery=50,
            probe_temperature=25.0,
            probe_rssi=200,
            probe_voltage=3.7,
            relay_status=1,
            relay_voltage=9.0,
        )
        device._device_state = mock_state
        yield device
