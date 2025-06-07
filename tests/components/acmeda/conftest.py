"""Define fixtures available for all Acmeda tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from menuai.components.acmeda.const import DOMAIN
from menuai.const import CONF_HOST
from menuai.core import menuai

from tests.common import MockConfigEntry


@pytest.fixture
def mock_config_entry(menuai: menuai) -> MockConfigEntry:
    """Return the default mocked config entry."""
    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "127.0.0.1"},
    )
    mock_config_entry.add_to_menuai(menuai)
    return mock_config_entry


@pytest.fixture
def mock_hub_run() -> Generator[AsyncMock]:
    """Mock the hub run method."""
    with patch("menuai.components.acmeda.hub.aiopulse.Hub.run") as mock_run:
        yield mock_run
