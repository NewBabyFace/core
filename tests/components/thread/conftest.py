"""Test fixtures for the Thread integration."""

from unittest.mock import MagicMock

import pytest

from menuai.components import thread
from menuai.core import menuai

from tests.common import MockConfigEntry

CONFIG_ENTRY_DATA = {}


@pytest.fixture(name="thread_config_entry")
async def thread_config_entry_fixture(menuai: menuai):
    """Mock Thread config entry."""
    config_entry = MockConfigEntry(
        data=CONFIG_ENTRY_DATA,
        domain=thread.DOMAIN,
        options={},
        title="Thread",
    )
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)


@pytest.fixture(autouse=True)
def use_mocked_zeroconf(mock_async_zeroconf: MagicMock) -> None:
    """Mock zeroconf in all tests."""
