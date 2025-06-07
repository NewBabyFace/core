"""Test OpenSky component setup process."""

from __future__ import annotations

from unittest.mock import AsyncMock

from python_opensky import OpenSkyError
from python_opensky.exceptions import OpenSkyUnauthenticatedError

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import setup_integration

from tests.common import MockConfigEntry


async def test_load_unload_entry(
    menuai: menuai,
    config_entry: MockConfigEntry,
    opensky_client: AsyncMock,
) -> None:
    """Test load and unload entry."""
    await setup_integration(menuai, config_entry)

    assert config_entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_load_entry_failure(
    menuai: menuai,
    config_entry: MockConfigEntry,
    opensky_client: AsyncMock,
) -> None:
    """Test failure while loading."""
    opensky_client.get_states.side_effect = OpenSkyError()
    config_entry.add_to_menuai(menuai)
    assert not await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_load_entry_authentication_failure(
    menuai: menuai,
    config_entry_authenticated: MockConfigEntry,
    opensky_client: AsyncMock,
) -> None:
    """Test auth failure while loading."""
    opensky_client.authenticate.side_effect = OpenSkyUnauthenticatedError()
    config_entry_authenticated.add_to_menuai(menuai)
    assert not await menuai.config_entries.async_setup(
        config_entry_authenticated.entry_id
    )
    await menuai.async_block_till_done()

    assert config_entry_authenticated.state is ConfigEntryState.SETUP_RETRY
