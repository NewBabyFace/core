"""Test Mikrotik setup process."""

from unittest.mock import MagicMock, patch

from librouteros.exceptions import ConnectionClosed, LibRouterosError
import pytest

from menuai.components import mikrotik
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import MOCK_DATA

from tests.common import MockConfigEntry


@pytest.fixture(autouse=True)
def mock_api():
    """Mock api."""
    with (
        patch("librouteros.create_transport"),
        patch("librouteros.Api.readResponse") as mock_api,
    ):
        yield mock_api


async def test_successful_config_entry(menuai: menuai) -> None:
    """Test config entry successful setup."""
    entry = MockConfigEntry(
        domain=mikrotik.DOMAIN,
        data=MOCK_DATA,
    )
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.LOADED


async def test_hub_connection_error(menuai: menuai, mock_api: MagicMock) -> None:
    """Test setup fails due to connection error."""
    entry = MockConfigEntry(
        domain=mikrotik.DOMAIN,
        data=MOCK_DATA,
    )
    entry.add_to_menuai(menuai)

    mock_api.side_effect = ConnectionClosed

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_hub_authentication_error(
    menuai: menuai, mock_api: MagicMock
) -> None:
    """Test setup fails due to authentication error."""
    entry = MockConfigEntry(
        domain=mikrotik.DOMAIN,
        data=MOCK_DATA,
    )
    entry.add_to_menuai(menuai)

    mock_api.side_effect = LibRouterosError("invalid user name or password")

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR


async def test_unload_entry(menuai: menuai) -> None:
    """Test unloading an entry."""
    entry = MockConfigEntry(
        domain=mikrotik.DOMAIN,
        data=MOCK_DATA,
    )
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
