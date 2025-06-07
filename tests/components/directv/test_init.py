"""Tests for the DirecTV integration."""

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import setup_integration

from tests.test_util.aiohttp import AiohttpClientMocker


async def test_config_entry_not_ready(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test the DirecTV configuration entry not ready."""
    entry = await setup_integration(menuai, aioclient_mock, setup_error=True)

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload_config_entry(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test the DirecTV configuration entry unloading."""
    entry = await setup_integration(menuai, aioclient_mock)

    assert entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
