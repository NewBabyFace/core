"""Fixtures for Season integration tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import patch

import pytest

from menuai.components.season.const import DOMAIN, TYPE_ASTRONOMICAL
from menuai.const import CONF_TYPE

from tests.common import MockConfigEntry


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return the default mocked config entry."""
    return MockConfigEntry(
        title="Season",
        domain=DOMAIN,
        data={CONF_TYPE: TYPE_ASTRONOMICAL},
        unique_id=TYPE_ASTRONOMICAL,
    )


@pytest.fixture
def mock_setup_entry() -> Generator[None]:
    """Mock setting up a config entry."""
    with patch("menuai.components.season.async_setup_entry", return_value=True):
        yield
