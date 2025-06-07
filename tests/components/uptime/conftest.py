"""Fixtures for Uptime integration tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import patch

import pytest

from menuai.components.uptime.const import DOMAIN
from menuai.core import menuai

from tests.common import MockConfigEntry


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return the default mocked config entry."""
    return MockConfigEntry(
        title="Uptime",
        domain=DOMAIN,
    )


@pytest.fixture
def mock_setup_entry() -> Generator[None]:
    """Mock setting up a config entry."""
    with patch("menuai.components.uptime.async_setup_entry", return_value=True):
        yield


@pytest.fixture
async def init_integration(
    menuai: menuai, mock_config_entry: MockConfigEntry
) -> MockConfigEntry:
    """Set up the Uptime integration for testing."""
    mock_config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    return mock_config_entry
