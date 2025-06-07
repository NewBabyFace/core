"""Tests for the ATAG integration."""

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import init_integration, mock_connection

from tests.test_util.aiohttp import AiohttpClientMocker


async def test_config_entry_not_ready(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test configuration entry not ready on library error."""
    mock_connection(aioclient_mock, conn_error=True)
    entry = await init_integration(menuai, aioclient_mock)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload_config_entry(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test the ATAG configuration entry unloading."""
    entry = await init_integration(menuai, aioclient_mock)
    assert entry.runtime_data
    await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()
    assert not hasattr(entry, "runtime_data")
