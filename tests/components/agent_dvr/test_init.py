"""Test Agent DVR integration."""

from unittest.mock import AsyncMock, patch

from agent import AgentError

from menuai.components.agent_dvr.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import CONF_DATA, create_entry, init_integration

from tests.test_util.aiohttp import AiohttpClientMocker


async def _create_mocked_agent(available: bool = True):
    mocked_agent = AsyncMock()
    mocked_agent.is_available = available
    return mocked_agent


def _patch_init_agent(mocked_agent):
    return patch(
        "menuai.components.agent_dvr.Agent",
        return_value=mocked_agent,
    )


async def test_setup_config_and_unload(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test setup and unload."""
    entry = await init_integration(menuai, aioclient_mock)
    assert entry.state is ConfigEntryState.LOADED
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.data == CONF_DATA

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_async_setup_entry_not_ready(menuai: menuai) -> None:
    """Test that it throws ConfigEntryNotReady when exception occurs during setup."""
    entry = create_entry(menuai)
    with patch(
        "menuai.components.agent_dvr.Agent.update",
        side_effect=AgentError,
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY
    with _patch_init_agent(await _create_mocked_agent(available=False)):
        await menuai.config_entries.async_reload(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY
