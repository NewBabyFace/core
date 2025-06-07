"""eafm fixtures."""

from unittest.mock import patch

import pytest


@pytest.fixture
def mock_get_stations():
    """Mock aioeafm.get_stations."""
    with patch("menuai.components.eafm.config_flow.get_stations") as patched:
        yield patched


@pytest.fixture
def mock_get_station():
    """Mock aioeafm.get_station."""
    with patch("menuai.components.eafm.coordinator.get_station") as patched:
        yield patched
