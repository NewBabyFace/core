"""Provide common mystrom fixtures and mocks."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from menuai.components.mystrom.const import DOMAIN
from menuai.const import CONF_HOST
from menuai.core import menuai

from tests.common import MockConfigEntry

DEVICE_NAME = "myStrom Device"
DEVICE_MAC = "6001940376EB"


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "menuai.components.mystrom.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture
def config_entry(menuai: menuai) -> MockConfigEntry:
    """Create and add a config entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DEVICE_MAC,
        data={CONF_HOST: "1.1.1.1"},
        title=DEVICE_NAME,
    )
    config_entry.add_to_menuai(menuai)
    return config_entry
